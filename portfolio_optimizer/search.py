"""Search Yahoo Finance for funds, ETFs, ETCs and shares by name, ISIN or ticker.

Finect, Morningstar or Financial Hub have no public API; Yahoo's search is free
and covers most European funds under their Morningstar ids (``0P...F``), which
is why it is the engine here. Results without price history are dropped, so
everything the user can add will actually load.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from .catalog import Instrument, find, is_isin
from .classify import guess_instrument

ALLOWED_TYPES = {"ETF", "MUTUALFUND", "EQUITY", "CRYPTOCURRENCY"}


def _history_info(symbol: str) -> tuple[int, str]:
    import yfinance as yf

    try:
        h = yf.Ticker(symbol).history(period="max", auto_adjust=True)
    except Exception:
        return 0, ""
    return len(h), (str(h.index[0].date()) if len(h) else "")


def search_instruments(query: str, max_results: int = 10, min_obs: int = 60) -> list[dict]:
    """Yahoo search with history check. Each hit: symbol, name, type, exchange, start, observations, instrument."""
    import yfinance as yf

    query = query.strip()
    if len(query) < 2:
        return []
    found = find(query)
    quotes = yf.Search(query, max_results=max(max_results * 2, 10)).quotes
    quotes = [q for q in quotes if (q.get("quoteType") or "").upper() in ALLOWED_TYPES and q.get("symbol")]
    with ThreadPoolExecutor(max_workers=8) as pool:
        infos = list(pool.map(lambda q: _history_info(q["symbol"]), quotes))
    hits = []
    for q, (n, start) in zip(quotes, infos):
        if n < min_obs:
            continue
        name = q.get("longname") or q.get("shortname") or q["symbol"]
        isin = query.upper() if is_isin(query) else ""
        inst = guess_instrument(q["symbol"], name, q.get("quoteType", ""), isin)
        hits.append({"symbol": q["symbol"], "name": name, "type": q.get("quoteType", ""),
                     "exchange": q.get("exchDisp") or q.get("exchange", ""), "start": start, "observations": n,
                     "instrument": inst})
        if len(hits) >= max_results:
            break
    if found is not None:                     # a catalogue match always comes first
        hits.insert(0, {"symbol": found.symbol, "name": found.name, "type": found.kind, "exchange": "",
                        "start": "", "observations": 0, "instrument": found})
    return hits


def instrument_to_dict(inst: Instrument) -> dict:
    d = {k: v for k, v in inst.__dict__.items() if k != "tags"}
    d["exposure"] = [list(e) for e in inst.exposure]
    return d


def instrument_from_dict(d: dict) -> Instrument:
    d = dict(d)
    d["exposure"] = tuple(tuple(e) for e in d.get("exposure", ()))
    d.pop("tags", None)
    return Instrument(**d)
