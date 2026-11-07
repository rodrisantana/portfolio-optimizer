"""Guess how to classify an instrument from its name and Yahoo quote type.

Used for anything that is not in the curated catalogue: products found with
the search box or imported from a broker file. The guess is only a starting
point; every field stays editable in the app's instrument table.
"""

from __future__ import annotations

import re

from .catalog import COMMODITIES, CRYPTO, EQUITY, FIXED_INCOME, MIXED, MONEY_MARKET, Instrument, is_isin

_RULES_CLASS = [
    (MONEY_MARKET, r"money market|monetari|liquidit|liquidez|tr[eé]sorerie|overnight|\bestr\b|€str|insticash|\bcash\b"),
    (MIXED, r"mixt|mixed|balanced|multi[- ]?asset|patrimoni|permanente|allocation|flexib|defensiv|moderad|equilibrad"),
    (FIXED_INCOME, r"bond|\bbd\b|renta fija|govt|government|treasur|aggregate|\bagg\b|corporate|\bcorp\b|credit|"
                   r"fixed inc|income|obligacion|deuda|floating rate|ultra ?short|short term|\bgilt|tips\b|bund|"
                   r"high yield|renta fija"),
    (COMMODITIES, r"\bgold\b|\boro\b|silver|\bplata\b|commodit|materias primas|platinum|xetra-gold"),
    (CRYPTO, r"bitcoin|ethereum|crypto|\bbtc\b|\beth\b"),
]
_RULES_REGION = [
    ("Emerging", r"emerging|emergent|\bem\b|\bem imi\b"),
    ("Japan", r"japan|jap[oó]n|nikkei|topix"),
    ("Eurozone", r"\bemu\b|euro stoxx|eurozone|zona euro|eurozona"),
    ("Europe", r"europe|europa|stoxx 600|ftse 100|\bdax\b|ibex|cac 40"),
    ("US", r"s&p|s\+p|\busa\b|u\.s\.|\bus\b|america|nasdaq|dow jones|russell"),
    ("Global", r"world|global|acwi|all[- ]world|mundial|internacional|international|developed"),
]
_RULES_CATEGORY = [
    ("Govt", r"govt|government|treasur|deuda p[uú]blica|bund|gilt|govies"),
    ("Inflation-linked", r"inflation|tips\b|linked"),
    ("Corporate", r"corporate|\bcorp\b|credit|cr[eé]dito"),
    ("Short-term", r"ultra ?short|short term|corto plazo|floating rate|1-3"),
    ("Income", r"income|high yield"),
    ("Gold", r"\bgold\b|\boro\b|xetra-gold"),
    ("Small cap", r"small ?cap|peque[ñn]as"),
    ("Value", r"\bvalue\b|valor"),
    ("Growth", r"growth|crecimiento|nasdaq|technolog|tecnolog"),
    ("Quality", r"quality|calidad"),
]
_INDEX_HINT = r"index|indexad|\bidx\b|msci|s&p|ftse|stoxx|nasdaq|\btracker\b|core "

# Typical costs used when the real TER is unknown (shown as an estimate, editable).
TYPICAL_TER = {"ETF": 0.0020, "ETC": 0.0020, "ETN": 0.0080, "Index fund": 0.0030, "Active fund": 0.0150,
               "Pension plan": 0.0100, "Stock": 0.0, "Spot": 0.0}
DEFAULT_PROXY = {
    (EQUITY, "Global"): "EUNL.DE", (EQUITY, "US"): "SXR8.DE", (EQUITY, "Europe"): "IMAE.AS",
    (EQUITY, "Eurozone"): "SXR7.DE", (EQUITY, "Emerging"): "IS3N.DE",
    (MONEY_MARKET, None): "XEON.DE", (COMMODITIES, None): "4GLD.DE",
}


def _first(rules, text: str, default):
    for value, pattern in rules:
        if re.search(pattern, text):
            return value
    return default


def guess_kind(name: str, quote_type: str) -> str:
    n = name.lower()
    qt = (quote_type or "").upper()
    if qt == "EQUITY":
        return "Stock"
    if qt == "CRYPTOCURRENCY":
        return "Spot"
    if qt == "ETF" or re.search(r"\betf\b|ucits etf", n):
        if re.search(r"\betc\b|physical|xetra-gold|\bgold\b|silver", n):
            return "ETC"
        if re.search(r"\betn\b", n):
            return "ETN"
        return "ETF"
    if re.search(r"\bpp\b|plan de pensiones|pension plan|\bpension", n):
        return "Pension plan"
    return "Index fund" if re.search(_INDEX_HINT, n) else "Active fund"


def guess_instrument(symbol: str, name: str, quote_type: str = "", isin: str = "") -> Instrument:
    """Best-effort classification of an unknown product."""
    text = f" {name.lower()} "
    kind = guess_kind(name, quote_type)
    asset_class = _first(_RULES_CLASS, text, EQUITY)
    region = _first(_RULES_REGION, text, "Global")
    if asset_class in (MONEY_MARKET,):
        region = "Eurozone" if region == "Global" else region
    if asset_class in (COMMODITIES, CRYPTO):
        region = "n/a"
    category = _first(_RULES_CATEGORY, text, "Broad")
    if asset_class == MONEY_MARKET:
        category = "Cash"
    exposure = ((EQUITY, 0.5), (FIXED_INCOME, 0.5)) if asset_class == MIXED else ()
    proxy = ""
    if kind not in ("Stock", "Spot"):
        if asset_class == FIXED_INCOME:
            proxy = {"Short-term": "ERNE.AS", "Corporate": "IEAC.AS", "Govt": "SXRQ.DE"}.get(category, "EUNA.DE")
        elif asset_class == MIXED:
            proxy = "EUNL.DE:0.5,EUNA.DE:0.5"
        else:
            proxy = DEFAULT_PROXY.get((asset_class, region)) or DEFAULT_PROXY.get((asset_class, None), "")
    management = "Active" if kind == "Active fund" else "Passive"
    short = name if len(name) <= 28 else name[:27].rstrip() + "…"
    return Instrument(symbol, name, kind, asset_class, TYPICAL_TER.get(kind, 0.0),
                      isin if is_isin(isin) else "", region, category, management, proxy, exposure,
                      note="Classified automatically and TER estimated: check them in the instrument table.",
                      short=short)
