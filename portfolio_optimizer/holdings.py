"""Your real portfolio: current weights, rebalancing plans and Spanish tax impact.

Spain-specific rules modelled here (IRPF, savings income):

* Gains on ETFs, ETCs and shares are taxed when you sell.
* Switching between investment funds ("traspaso", art. 94 LIRPF) defers the
  tax, so selling a fund to buy another fund is tax-free today. This is why
  index funds are popular in Spain even with slightly higher TERs.
* Savings-base brackets (2025 onwards): 19% up to 6,000 EUR, 21% to 50,000,
  23% to 200,000, 27% to 300,000 and 30% above.

The tax estimate uses average cost (Spain actually applies FIFO per lot) and
ignores offsetting losses, so treat it as an order of magnitude.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .catalog import describe

SAVINGS_BRACKETS_ES = ((6_000, 0.19), (50_000, 0.21), (200_000, 0.23), (300_000, 0.27), (float("inf"), 0.30))


def spanish_savings_tax(gain: float) -> float:
    """Progressive tax on a net capital gain under the Spanish savings base."""
    if gain <= 0:
        return 0.0
    tax, lower = 0.0, 0.0
    for upper, rate in SAVINGS_BRACKETS_ES:
        if gain <= lower:
            break
        tax += (min(gain, upper) - lower) * rate
        lower = upper
    return tax


@dataclass
class Holding:
    asset: str
    value: float               # current market value in base currency
    cost_basis: float = 0.0    # total amount paid; 0 means unknown

    @property
    def unrealised_gain(self) -> float:
        return self.value - self.cost_basis if self.cost_basis > 0 else 0.0


def current_weights(holdings: list[Holding], universe: list[str]) -> pd.Series:
    values = pd.Series({h.asset: h.value for h in holdings}, dtype=float).reindex(universe).fillna(0.0)
    total = values.sum()
    if total <= 0:
        raise ValueError("Enter the current value of at least one position.")
    return values / total


def rebalance_plan(holdings: list[Holding], target: pd.Series, new_cash: float = 0.0,
                   allow_sells: bool = False, is_fund: dict[str, bool] | None = None) -> pd.DataFrame:
    """Trades that move the portfolio to ``target``.

    With ``allow_sells=False`` (the default) only the new cash is used: it goes
    to the most underweight assets first, which is the cheapest way to
    rebalance because nothing is sold and no tax is triggered. With sells
    allowed, the result is an exact rebalance and the tax column estimates the
    IRPF on each sale (zero for index funds moved by traspaso).
    """
    assets = list(target.index)
    current = pd.Series({h.asset: h.value for h in holdings}, dtype=float).reindex(assets).fillna(0.0)
    cost = pd.Series({h.asset: h.cost_basis for h in holdings}, dtype=float).reindex(assets).fillna(0.0)
    total_after = current.sum() + new_cash
    desired = target * total_after
    gap = desired - current

    if allow_sells:
        trade = gap
    else:
        if new_cash < 0:
            raise ValueError("Use allow_sells=True to plan a withdrawal.")
        buys = gap.clip(lower=0.0)
        if buys.sum() > new_cash:
            trade = buys * (new_cash / buys.sum()) if buys.sum() > 0 else buys
        else:
            # every gap can be closed; spread the rest by target weight
            trade = buys + (new_cash - buys.sum()) * target

    sells = (-trade).clip(lower=0.0)
    gain_ratio = np.where((current > 0) & (cost > 0), 1.0 - cost / current.replace(0, np.nan), 0.0)
    realised = pd.Series(np.nan_to_num(sells.values * gain_ratio), index=assets) + 0.0   # no "-0.00"
    flags = is_fund or {}
    is_fund = pd.Series([flags.get(a, describe(a).is_fund) for a in assets], index=assets, dtype=bool)
    # Fund sales whose proceeds go to other funds can use a traspaso.
    taxable_gain = realised.where(~is_fund, 0.0).clip(lower=0.0)
    total_tax = spanish_savings_tax(float(taxable_gain.sum()))
    tax_share = taxable_gain / taxable_gain.sum() if taxable_gain.sum() > 0 else taxable_gain * 0

    after = current + trade
    out = pd.DataFrame({
        "Current value": current,
        "Current weight": current / current.sum() if current.sum() > 0 else current,
        "Target weight": target,
        "Trade": trade + 0.0,
        "Value after": after,
        "Weight after": after / after.sum() if after.sum() > 0 else after,
        "Realised gain": realised,
        "Estimated tax": tax_share * total_tax + 0.0,
        "Traspaso eligible": is_fund,
    })
    out.index.name = "Asset"
    return out


def tracking_gap(current: pd.Series, target: pd.Series) -> float:
    """Half the sum of absolute weight differences: the share of the portfolio that is 'misplaced'."""
    c, t = current.align(target, fill_value=0.0)
    return float(np.abs(c - t).sum() / 2)
