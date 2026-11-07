"""Market data: download, currency conversion, cleaning and alignment.

The pipeline is

    identifier (ticker or ISIN)
      -> Yahoo symbol            resolve_symbol()
      -> local-currency prices   fetch_history()   (cached on disk)
      -> base-currency prices    to_base_currency()
      -> one aligned DataFrame   load_prices()
      -> periodic returns        to_returns()

Everything after the download is pure pandas, so it is unit-tested offline.
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from .catalog import describe, is_isin

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = PROJECT_ROOT / "data" / "cache"
DEMO_PATH = PROJECT_ROOT / "data" / "demo_prices.csv"

PERIODS_PER_YEAR = {"daily": 252, "weekly": 52, "monthly": 12}
_RESAMPLE_RULE = {"weekly": "W-FRI", "monthly": "ME"}

# Quotes in minor units: price / divisor gives the major currency.
MINOR_UNITS = {"GBp": ("GBP", 100.0), "GBX": ("GBP", 100.0), "ZAc": ("ZAR", 100.0), "ILA": ("ILS", 100.0)}


@dataclass
class PriceData:
    """Aligned prices in one base currency, plus what happened on the way."""

    prices: pd.DataFrame
    base_currency: str
    currencies: dict[str, str] = field(default_factory=dict)   # original quote currency per column
    resolved: dict[str, str] = field(default_factory=dict)     # identifier -> Yahoo symbol
    backfilled: dict[str, str] = field(default_factory=dict)   # column -> proxy used
    warnings: list[str] = field(default_factory=list)

    @property
    def start(self) -> pd.Timestamp:
        return self.prices.index[0]

    @property
    def end(self) -> pd.Timestamp:
        return self.prices.index[-1]


# --------------------------------------------------------------------------- download
def _yf():
    import yfinance as yf  # imported lazily: the offline parts never need it

    return yf


def resolve_symbol(identifier: str) -> str:
    """Map an ISIN to the Yahoo symbol of its main listing; tickers pass through."""
    identifier = identifier.strip()
    if not is_isin(identifier):
        return identifier.upper() if "=" not in identifier else identifier
    cache = CACHE_DIR / "isin_map.json"
    mapping = json.loads(cache.read_text()) if cache.exists() else {}
    if identifier in mapping:
        return mapping[identifier]
    symbol = _yf().Ticker(identifier).ticker
    if not symbol or symbol == identifier:
        raise ValueError(f"Yahoo Finance does not know ISIN {identifier}. Upload its NAV history as a CSV instead.")
    mapping[identifier] = symbol
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(mapping, indent=2, sort_keys=True))
    return symbol


def _cache_file(symbol: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in symbol)
    return CACHE_DIR / f"{safe}.csv"


def fetch_history(symbol: str, refresh: bool = False, max_age_days: int = 1) -> tuple[pd.Series, str]:
    """Total-return price series (dividends reinvested) and its quote currency.

    Results are cached on disk; the cache is refreshed when it is older than
    ``max_age_days`` or when ``refresh`` is set.
    """
    path = _cache_file(symbol)
    meta_path = path.with_suffix(".json")
    if path.exists() and meta_path.exists() and not refresh:
        meta = json.loads(meta_path.read_text())
        age = pd.Timestamp.now() - pd.Timestamp(meta["downloaded"])
        if age <= pd.Timedelta(days=max_age_days):
            s = pd.read_csv(path, index_col=0, parse_dates=True).iloc[:, 0]
            return s.rename(symbol), meta["currency"]

    ticker = _yf().Ticker(symbol)
    hist = ticker.history(period="max", auto_adjust=True, actions=False)
    if hist.empty:
        raise ValueError(f"No price data returned for {symbol}.")
    currency = (ticker.history_metadata or {}).get("currency") or "USD"
    s = hist["Close"].copy()
    s.index = pd.DatetimeIndex(s.index).tz_localize(None).normalize()
    s = s[~s.index.duplicated(keep="last")].dropna().rename(symbol)

    path.parent.mkdir(parents=True, exist_ok=True)
    s.to_csv(path)
    meta_path.write_text(json.dumps({"currency": currency, "downloaded": pd.Timestamp.now().isoformat()}))
    return s, currency


def fetch_fx(base: str, quote: str, refresh: bool = False) -> pd.Series:
    """Units of ``quote`` per one unit of ``base`` (e.g. EURUSD=X: USD per EUR)."""
    s, _ = fetch_history(f"{base}{quote}=X", refresh=refresh)
    return s


# --------------------------------------------------------------------------- pure transforms
def normalise_minor_units(prices: pd.Series, currency: str) -> tuple[pd.Series, str]:
    """GBp -> GBP and friends. Without this, LSE prices are 100x too large."""
    if currency in MINOR_UNITS:
        major, divisor = MINOR_UNITS[currency]
        return prices / divisor, major
    return prices, currency


def to_base_currency(prices: pd.Series, currency: str, base: str, fx: pd.Series | None) -> pd.Series:
    """Convert a price series quoted in ``currency`` into ``base``.

    ``fx`` must be quoted as units of ``currency`` per one ``base``. The FX
    series is forward-filled onto the asset's own dates, so a missing FX print
    never deletes a price.
    """
    if currency == base:
        return prices
    if fx is None:
        raise ValueError(f"FX series {base}{currency} is required to convert {prices.name}.")
    rate = fx.reindex(prices.index.union(fx.index)).sort_index().ffill().reindex(prices.index)
    converted = prices / rate
    return converted.dropna()


def remove_spikes(prices: pd.Series, threshold: float = 0.25) -> tuple[pd.Series, int]:
    """Drop one-day bad ticks: a jump of more than ``threshold`` that fully reverts the next day.

    Yahoo data for European listings sometimes contains a single absurd print
    (e.g. a price 10x too high for one day). One such point inflates the
    estimated volatility enormously, so it is replaced by the previous price.
    Genuine moves that do not revert are kept.
    """
    p = prices.copy()
    r = p.pct_change()
    nxt = r.shift(-1)
    bad = (r.abs() > threshold) & (nxt.abs() > threshold * 0.7) & (np.sign(r) != np.sign(nxt))
    count = int(bad.sum())
    if count:
        p[bad] = np.nan
        p = p.ffill()
    return p, count


def align(series: dict[str, pd.Series], ffill_limit: int = 5) -> pd.DataFrame:
    """Join price series on a common calendar.

    Exchanges have different holidays, so prices are forward-filled for at most
    ``ffill_limit`` days (a holiday then shows as a zero return, which is what
    actually happened to the investor). Rows before the youngest asset starts
    are dropped.
    """
    if not series:
        raise ValueError("No price series to align.")
    df = pd.concat(series, axis=1).sort_index()
    df = df.ffill(limit=ffill_limit)
    first_valid = max(df[c].first_valid_index() for c in df.columns)
    df = df.loc[first_valid:]
    df = df.dropna(how="any")
    if len(df) < 30:
        raise ValueError("Fewer than 30 overlapping observations. Pick assets with a longer common history.")
    return df


def backfill_with_proxy(target: pd.Series, proxy: pd.Series) -> pd.Series:
    """Extend ``target`` backwards using the proxy's returns before ``target`` starts.

    The spliced series is scaled so that it joins the real one with no jump.
    """
    target = target.dropna()
    proxy = proxy.dropna()
    start = target.index[0]
    if proxy.index[0] >= start:
        return target
    anchor_date = proxy.index[proxy.index <= start][-1]   # last proxy print on/before the join
    scale = target.iloc[0] / proxy.loc[anchor_date]
    head = proxy.loc[proxy.index < start] * scale
    return pd.concat([head, target]).rename(target.name)


def to_returns(prices: pd.DataFrame, frequency: str = "weekly") -> pd.DataFrame:
    """Simple returns at the chosen frequency.

    Weekly is the default for estimation: daily closes from Frankfurt, London
    and New York are not synchronous, which biases daily correlations towards
    zero. Weekly returns remove most of that bias while keeping enough points.
    """
    if frequency not in PERIODS_PER_YEAR:
        raise ValueError(f"frequency must be one of {list(PERIODS_PER_YEAR)}")
    if frequency != "daily":
        prices = prices.resample(_RESAMPLE_RULE[frequency]).last()
    return prices.pct_change().dropna(how="any")


def parse_uploaded_csv(content: bytes | str, name: str = "upload") -> pd.DataFrame:
    """Read a user CSV of prices/NAVs: first column dates, one column per asset.

    Accepts comma or semicolon separators and European decimal commas, which is
    what Spanish fund managers and Morningstar exports usually contain.
    """
    text = content.decode("utf-8-sig") if isinstance(content, bytes) else content
    first_line = text.splitlines()[0] if text else ""
    sep = ";" if first_line.count(";") > first_line.count(",") else ","
    decimal = "," if sep == ";" else "."
    df = pd.read_csv(io.StringIO(text), sep=sep, decimal=decimal)
    if df.shape[1] < 2:
        raise ValueError(f"{name}: expected a date column plus at least one price column.")
    dates = pd.to_datetime(df.iloc[:, 0], dayfirst=_looks_dayfirst(df.iloc[:, 0]), errors="coerce")
    df = df.iloc[:, 1:].set_index(dates)
    df = df[df.index.notna()].sort_index()
    df = df.apply(pd.to_numeric, errors="coerce")
    df.index.name = "Date"
    if df.dropna(how="all").empty:
        raise ValueError(f"{name}: no numeric prices found.")
    return df


def _looks_dayfirst(col: pd.Series) -> bool:
    sample = col.astype(str).head(50)
    firsts = sample.str.extract(r"^(\d{1,2})[/.-]")[0].dropna().astype(int)
    return bool(len(firsts)) and firsts.max() > 12


def load_demo() -> PriceData:
    """Offline dataset (EUR prices) shipped with the repo, used by tests and as a fallback."""
    df = pd.read_csv(DEMO_PATH, index_col=0, parse_dates=True)
    return PriceData(prices=df, base_currency="EUR", currencies={c: "EUR" for c in df.columns},
                     resolved={c: c for c in df.columns})


# --------------------------------------------------------------------------- orchestration
def load_prices(
    identifiers: list[str],
    base_currency: str = "EUR",
    start: str | None = None,
    end: str | None = None,
    backfill: bool = True,
    clean_spikes: bool = True,
    uploaded: pd.DataFrame | None = None,
    refresh: bool = False,
) -> PriceData:
    """Download, convert and align everything the user selected.

    ``uploaded`` holds user-supplied price columns, assumed to be in the base
    currency already.
    """
    identifiers = list(dict.fromkeys(i.strip() for i in identifiers if i.strip()))
    warnings: list[str] = []
    resolved: dict[str, str] = {}
    raw: dict[str, tuple[pd.Series, str]] = {}

    def _get(identifier: str):
        symbol = resolve_symbol(identifier)
        return identifier, symbol, fetch_history(symbol, refresh=refresh)

    if identifiers:
        with ThreadPoolExecutor(max_workers=min(8, len(identifiers))) as pool:
            futures = [pool.submit(_get, i) for i in identifiers]
            for f in futures:
                try:
                    identifier, symbol, (series, ccy) = f.result()
                except Exception as exc:  # report and continue with the rest
                    warnings.append(f"Skipped: {exc}")
                    continue
                resolved[identifier] = symbol
                raw[identifier] = (series, ccy)

    fx_cache: dict[str, pd.Series] = {}
    converted: dict[str, pd.Series] = {}
    currencies: dict[str, str] = {}
    for identifier, (series, ccy) in raw.items():
        series, ccy = normalise_minor_units(series, ccy)
        currencies[identifier] = ccy
        if ccy != base_currency and ccy not in fx_cache:
            fx_cache[ccy] = fetch_fx(base_currency, ccy, refresh=refresh)
        series = to_base_currency(series, ccy, base_currency, fx_cache.get(ccy))
        if clean_spikes and describe(identifier).asset_class != "Crypto":
            series, n = remove_spikes(series)
            if n:
                warnings.append(f"{identifier}: removed {n} one-day bad print(s) from the Yahoo data.")
        converted[identifier] = series.rename(identifier)

    backfilled: dict[str, str] = {}
    if backfill:
        for identifier, series in list(converted.items()):
            proxy_symbol = describe(identifier).proxy
            if not proxy_symbol:
                continue
            try:
                proxy, pccy = fetch_history(proxy_symbol, refresh=refresh)
                proxy, pccy = normalise_minor_units(proxy, pccy)
                if pccy != base_currency:
                    proxy = to_base_currency(proxy, pccy, base_currency, fetch_fx(base_currency, pccy))
                filled = backfill_with_proxy(series, proxy)
                if filled.index[0] < series.index[0]:
                    converted[identifier] = filled
                    backfilled[identifier] = proxy_symbol
            except Exception as exc:
                warnings.append(f"{identifier}: proxy backfill failed ({exc}).")

    if uploaded is not None and not uploaded.empty:
        for col in uploaded.columns:
            converted[str(col)] = uploaded[col].dropna().rename(str(col))
            currencies[str(col)] = base_currency

    prices = align(converted)
    if start:
        prices = prices.loc[pd.Timestamp(start):]
    if end:
        prices = prices.loc[: pd.Timestamp(end)]
    if len(prices) < 30:
        raise ValueError("The chosen date range leaves fewer than 30 observations.")
    order = [i for i in identifiers if i in prices.columns] + [c for c in prices.columns if c not in identifiers]
    return PriceData(prices=prices[order], base_currency=base_currency, currencies=currencies,
                     resolved=resolved, backfilled=backfilled, warnings=warnings)


def fingerprint(prices: pd.DataFrame) -> str:
    """Stable hash of a price frame, handy as a cache key."""
    h = hashlib.sha1(pd.util.hash_pandas_object(prices, index=True).values.tobytes())
    return h.hexdigest()[:12]
