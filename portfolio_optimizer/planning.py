"""Savings plans: deterministic projections, historical monthly investing and money-weighted returns."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import brentq


def projection_table(initial: float, monthly: float, years: int, annual_return: float,
                     contribution_growth: float = 0.0, inflation: float = 0.0) -> pd.DataFrame:
    """Year-by-year value of a plan that earns exactly ``annual_return`` (net of fees).

    Contributions are paid at the end of each month and grow once a year by
    ``contribution_growth``. This is the 'expected path'; the Monte Carlo shows
    the spread around it.
    """
    rm = (1 + annual_return) ** (1 / 12) - 1
    value, contributed, rows = float(initial), float(initial), []
    for year in range(1, years + 1):
        c = monthly * (1 + contribution_growth) ** (year - 1)
        for _ in range(12):
            value = value * (1 + rm) + c
            contributed += c
        deflator = (1 + inflation) ** year
        rows.append({"Year": year, "Contributed": contributed, "Value": value, "Gains": value - contributed,
                     "Value (today's money)": value / deflator})
    return pd.DataFrame(rows).set_index("Year")


def xirr(cashflows: pd.Series) -> float:
    """Money-weighted annual return of dated cash flows (negative = money in, positive = money out)."""
    cf = cashflows[cashflows != 0]
    if len(cf) < 2 or (cf > 0).all() or (cf < 0).all():
        return float("nan")
    t = np.array([(d - cf.index[0]).days / 365.25 for d in cf.index])
    v = cf.values.astype(float)

    def npv(r: float) -> float:
        return float(np.sum(v / (1 + r) ** t))

    try:
        return float(brentq(npv, -0.99, 10.0, maxiter=500))
    except ValueError:
        return float("nan")


def historical_dca(wealth: pd.Series, monthly: float, initial: float = 0.0) -> tuple[pd.DataFrame, float]:
    """Invest ``initial`` on day one and ``monthly`` on the first trading day of every month.

    ``wealth`` is the portfolio's value index (any starting level, net of costs).
    Returns the daily value / contributed path and the money-weighted return (XIRR).
    """
    w = wealth.dropna()
    first_days = w.groupby([w.index.year, w.index.month]).head(1).index
    flows = pd.Series(0.0, index=w.index)
    flows.iloc[0] += initial
    flows.loc[first_days[1:]] += monthly
    if initial == 0:
        flows.iloc[0] += monthly
    units = (flows / w).cumsum()
    value = units * w
    path = pd.DataFrame({"Value": value, "Contributed": flows.cumsum()})
    cash = -flows.copy()
    cash.iloc[-1] += value.iloc[-1]
    return path, xirr(cash)
