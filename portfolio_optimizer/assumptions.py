"""Long-term capital market assumptions (CMAs).

Historical averages are a poor guide to the next 10-15 years: they are noisy
and they extrapolate whatever happened in the sample (2019-2026 was an
exceptional period for US equities and a poor one for bonds). Asset managers
publish forward-looking expected returns instead, built from today's
valuations, yields and growth.

The default set is J.P. Morgan Asset Management's *2027 Long-Term Capital
Market Assumptions*, euro-denominated table ("Euro assumptions", 10-15 year
horizon, published October 2026). For each asset class the report gives the
arithmetic mean return (used by the optimiser and the Monte Carlo, which needs
a mean) and the compound return (what a buy-and-hold investor earns per year,
shown for reference). Rows marked ``own`` are not in the report and are our
assumption. Every figure is editable in the app.

An instrument's expected return is its interest rate for accounts and deposits,
and otherwise

    E[r] = sum_c exposure_c * CMA(c, region, style)  -  TER  +  alpha (active funds only)

Active funds get ``alpha = 0`` by default: before costs, the average active
manager earns the market return, so after costs the average active fund lags
its index by roughly its fee difference (the conclusion of the SPIVA scorecards).
"""

from __future__ import annotations

import pandas as pd

from .catalog import COMMODITIES, CRYPTO, EQUITY, FIXED_INCOME, MONEY_MARKET, Instrument

JPM_SOURCE = "J.P. Morgan Asset Management, 2027 Long-Term Capital Market Assumptions, Euro assumptions"

# key -> (arithmetic mean, compound, source row in the report or "own")
JPM_2027_EUR: dict[str, tuple[float, float, str]] = {
    "Equity · Global": (0.0810, 0.0700, "AC World Equity"),
    "Equity · US": (0.0830, 0.0700, "U.S. Large Cap (unhedged, in EUR)"),
    "Equity · Europe": (0.0792, 0.0680, "European Large Cap"),
    "Equity · Eurozone": (0.0903, 0.0760, "Euro Area Large Cap"),
    "Equity · Emerging": (0.0797, 0.0660, "Emerging Markets Equity"),
    "Equity · Japan": (0.0965, 0.0860, "Japanese Equity"),
    "Equity · small cap / value premium": (0.0085, 0.0050, "European Small Cap minus Large Cap"),
    "Fixed income · Government": (0.0433, 0.0420, "Euro Government Bonds"),
    "Fixed income · Aggregate": (0.0477, 0.0470, "Global Multiverse Bonds hedged"),
    "Fixed income · Inflation-linked": (0.0467, 0.0450, "Euro Govt Inflation-Linked Bonds"),
    "Fixed income · Corporate": (0.0471, 0.0460, "Euro Inv Grade Corp Bonds"),
    "Fixed income · Short-term": (0.0310, 0.0310, "own: Euro Cash + 0.5"),
    "Fixed income · Income / high yield": (0.0631, 0.0590, "Euro High Yield Bonds"),
    "Money market": (0.0260, 0.0260, "Euro Cash"),
    "Commodities · Gold": (0.0621, 0.0500, "Gold"),
    "Commodities · Other": (0.0555, 0.0430, "Commodities"),
    "Crypto": (0.0260, 0.0260, "own: no expert forecast, no premium over cash assumed"),
}
JPM_EUR_INFLATION = 0.022          # "Euro Inflation", compound

# A more cautious set for comparison: round numbers below J.P. Morgan's.
CONSERVATIVE: dict[str, tuple[float, float, str]] = {
    "Equity · Global": (0.065, 0.055, "own"), "Equity · US": (0.060, 0.050, "own"),
    "Equity · Europe": (0.065, 0.055, "own"), "Equity · Eurozone": (0.065, 0.055, "own"),
    "Equity · Emerging": (0.070, 0.055, "own"), "Equity · Japan": (0.065, 0.055, "own"),
    "Equity · small cap / value premium": (0.005, 0.005, "own"),
    "Fixed income · Government": (0.030, 0.029, "own"), "Fixed income · Aggregate": (0.032, 0.031, "own"),
    "Fixed income · Inflation-linked": (0.029, 0.028, "own"), "Fixed income · Corporate": (0.035, 0.034, "own"),
    "Fixed income · Short-term": (0.024, 0.024, "own"), "Fixed income · Income / high yield": (0.045, 0.042, "own"),
    "Money market": (0.020, 0.020, "own"), "Commodities · Gold": (0.035, 0.025, "own"),
    "Commodities · Other": (0.030, 0.020, "own"), "Crypto": (0.020, 0.020, "own"),
}
PRESETS = {"J.P. Morgan LTCMA 2027 (EUR)": JPM_2027_EUR, "Conservative (own)": CONSERVATIVE}
DEFAULT_PRESET = "J.P. Morgan LTCMA 2027 (EUR)"
DEFAULT_CMA: dict[str, float] = {k: v[0] for k, v in JPM_2027_EUR.items()}
PREMIUM_STYLES = {"Small cap", "Small cap value", "Value"}


def preset_table(name: str) -> pd.DataFrame:
    rows = PRESETS[name]
    return pd.DataFrame({"Assumption": list(rows), "Mean %": [v[0] * 100 for v in rows.values()],
                         "Compound %": [v[1] * 100 for v in rows.values()],
                         "Source": [v[2] for v in rows.values()]})


def _component(asset_class: str, inst: Instrument, cma: dict[str, float]) -> float:
    if asset_class == EQUITY:
        region = inst.region if f"Equity · {inst.region}" in cma else "Global"
        r = cma[f"Equity · {region}"]
        if inst.category in PREMIUM_STYLES:
            r += cma.get("Equity · small cap / value premium", 0.0)
        return r
    if asset_class == FIXED_INCOME:
        key = {"Govt": "Government", "Inflation-linked": "Inflation-linked", "Corporate": "Corporate",
               "Short-term": "Short-term", "Income": "Income / high yield"}.get(inst.category, "Aggregate")
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
    """Forward-looking expected (mean) return of each asset, net of its TER.

    ``instruments`` maps the column label to its (possibly user-edited)
    description; ``ter`` overrides the catalogue TERs when given.
    """
    cma = {**DEFAULT_CMA, **(cma or {})}
    out = {}
    for label, inst in instruments.items():
        if inst.rate is not None:                       # account or deposit: you know the rate
            out[label] = inst.rate
            continue
        gross = sum(w * _component(c, inst, cma) for c, w in inst.exposures.items())
        fee = float(ter[label]) if ter is not None and label in ter else inst.ter
        alpha = active_alpha if inst.management == "Active" else 0.0
        out[label] = gross - fee + alpha
    return pd.Series(out)


def median_growth(mean: float, vol: float) -> float:
    """Annual growth rate of the median path for a log-normal return with this mean and volatility.

    A portfolio with a 7% average return and 15% volatility does not grow at 7%
    a year: volatility drag makes the typical (median) investor earn about
    mean - vol^2 / 2. Deterministic projections use this rate.
    """
    return (1 + mean) / (1 + (vol / (1 + mean)) ** 2) ** 0.5 - 1
