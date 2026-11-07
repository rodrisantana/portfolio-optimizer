"""Long-term capital market assumptions (CMAs).

Historical averages are a poor guide to the next 10-20 years: they are noisy
and they extrapolate whatever happened in the sample (2019-2026 was an
exceptional period for US equities and a terrible one for bonds). Asset
managers publish forward-looking expected returns instead, built from current
valuations, yields and growth. The defaults below are round numbers in the
middle of the ranges those houses published for euro investors in 2025-2026.
They are nominal, annual, in EUR, gross of fees, and fully editable in the app.

An instrument's expected return is

    E[r] = sum_c exposure_c * CMA(c, region, style)  -  TER  +  alpha (active funds only)

Active funds get ``alpha = 0`` by default: before costs, the average active
manager earns the market return, so after costs the average active fund lags
its index by roughly its fee difference (the conclusion of the SPIVA scorecards).
"""

from __future__ import annotations

import pandas as pd

from .catalog import COMMODITIES, CRYPTO, EQUITY, FIXED_INCOME, MONEY_MARKET, Instrument

# key -> expected annual return (decimal)
DEFAULT_CMA: dict[str, float] = {
    "Equity · Global": 0.065,
    "Equity · US": 0.060,
    "Equity · Europe": 0.070,
    "Equity · Eurozone": 0.070,
    "Equity · Emerging": 0.075,
    "Equity · Japan": 0.065,
    "Equity · small cap / value premium": 0.005,
    "Fixed income · Government": 0.030,
    "Fixed income · Aggregate": 0.032,
    "Fixed income · Inflation-linked": 0.029,
    "Money market": 0.020,
    "Commodities · Gold": 0.035,
    "Commodities · Other": 0.030,
    "Crypto": 0.080,
}
PREMIUM_STYLES = {"Small cap", "Small cap value", "Value"}


def _component(asset_class: str, inst: Instrument, cma: dict[str, float]) -> float:
    if asset_class == EQUITY:
        region = inst.region if f"Equity · {inst.region}" in cma else "Global"
        r = cma[f"Equity · {region}"]
        if inst.category in PREMIUM_STYLES:
            r += cma.get("Equity · small cap / value premium", 0.0)
        return r
    if asset_class == FIXED_INCOME:
        key = {"Govt": "Government", "Inflation-linked": "Inflation-linked"}.get(inst.category, "Aggregate")
        return cma[f"Fixed income · {key}"]
    if asset_class == MONEY_MARKET:
        return cma["Money market"]
    if asset_class == COMMODITIES:
        return cma["Commodities · Gold"] if inst.category == "Gold" else cma["Commodities · Other"]
    if asset_class == CRYPTO:
        return cma["Crypto"]
    return cma["Equity · Global"]


def long_term_returns(instruments: dict[str, Instrument], ter: pd.Series | None = None,
                      cma: dict[str, float] | None = None, active_alpha: float = 0.0) -> pd.Series:
    """Forward-looking expected return of each asset, net of its TER.

    ``instruments`` maps the column label to its (possibly user-edited)
    description; ``ter`` overrides the catalogue TERs when given.
    """
    cma = {**DEFAULT_CMA, **(cma or {})}
    out = {}
    for label, inst in instruments.items():
        gross = sum(w * _component(c, inst, cma) for c, w in inst.exposures.items())
        fee = float(ter[label]) if ter is not None and label in ter else inst.ter
        alpha = active_alpha if inst.management == "Active" else 0.0
        out[label] = gross - fee + alpha
    return pd.Series(out)
