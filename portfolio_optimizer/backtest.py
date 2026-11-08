"""Historical simulation with drifting weights, rebalancing, costs and fees.

Two kinds of strategy are supported:

* **Static weights**: a fixed target (e.g. your own portfolio, or 60/40),
  rebalanced back to target on a calendar schedule.
* **Walk-forward optimisation**: at every rebalance date the strategy only
  sees the trailing ``lookback`` window of data, re-estimates mu and Sigma and
  re-optimises. This is an honest out-of-sample test: the in-sample efficient
  frontier always looks great because it was fitted to the same data.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import estimators
from .data import PERIODS_PER_YEAR, to_returns
from .optimizer import Constraints, InfeasibleError, PortfolioOptimizer

REBALANCE_RULES = {"Monthly": "ME", "Quarterly": "QE", "Semi-annual": "6ME", "Annual": "YE", "Never": None}


@dataclass
class BacktestResult:
    name: str
    wealth: pd.Series            # value of 1 unit invested, net of costs and fees
    weights: pd.DataFrame        # target weights set at each rebalance date
    turnover: pd.Series          # one-way traded fraction of the portfolio at each rebalance
    costs_paid: float            # total transaction costs as a fraction of initial wealth (approx.)

    @property
    def returns(self) -> pd.Series:
        return self.wealth.pct_change().dropna()


def rebalance_dates(index: pd.DatetimeIndex, rule: str | None) -> list[pd.Timestamp]:
    """Last available trading day of every calendar period."""
    if rule is None:
        return []
    s = pd.Series(index, index=index)
    return list(s.resample(rule).last().dropna())


WeightFn = Callable[[pd.DataFrame], np.ndarray]


def run_backtest(prices: pd.DataFrame, weight_fn: WeightFn, name: str, rebalance: str = "Quarterly",
                 start: pd.Timestamp | None = None, cost_bps: float = 10.0,
                 ter: pd.Series | None = None) -> BacktestResult:
    """Simulate a strategy on daily prices.

    ``weight_fn`` receives all prices up to and including the decision date and
    returns target weights; this makes look-ahead impossible by construction.
    Trades happen at that day's close. ``cost_bps`` is charged on the traded
    value; ``ter`` (annual, per asset) is deducted daily from each holding.
    """
    prices = prices.dropna()
    daily = prices.pct_change().fillna(0.0)
    if ter is not None:
        fee = ter.reindex(prices.columns).fillna(0.0).values / 252.0
        daily = daily - fee
    start = prices.index[0] if start is None else max(pd.Timestamp(start), prices.index[0])
    index = prices.index[prices.index >= start]
    if len(index) < 2:
        raise ValueError("Backtest window is empty.")
    rule = REBALANCE_RULES.get(rebalance, rebalance)
    rebal = set(rebalance_dates(index, rule))

    values = np.zeros(len(index))
    w_hist, turn_hist = {}, {}
    holdings = None
    value = 1.0
    cost_rate = cost_bps / 1e4
    costs = 0.0
    r = daily.loc[index].values

    for k, date in enumerate(index):
        if k > 0:
            holdings = holdings * (1.0 + r[k])
            value = float(holdings.sum())
        if k == 0 or date in rebal:
            target = np.asarray(weight_fn(prices.loc[:date]), dtype=float)
            target = np.clip(target, 0, None)
            target = target / target.sum()
            current = holdings / value if holdings is not None else np.zeros_like(target)
            traded = float(np.abs(target - current).sum())
            if k == 0:
                traded = 1.0              # initial purchase
            cost = value * traded * cost_rate
            costs += cost
            value -= cost
            holdings = target * value
            w_hist[date] = target
            turn_hist[date] = traded / 2 if k > 0 else 1.0
        values[k] = value

    wealth = pd.Series(values, index=index, name=name)
    weights = pd.DataFrame(w_hist, index=prices.columns).T
    return BacktestResult(name, wealth, weights, pd.Series(turn_hist, name="turnover"), costs)


def static_weights(weights: pd.Series) -> WeightFn:
    def fn(prices_so_far: pd.DataFrame) -> np.ndarray:
        return weights.reindex(prices_so_far.columns).fillna(0.0).values
    return fn


def walk_forward(strategy: str, lookback_years: float = 3.0, frequency: str = "weekly",
                 return_method: str = "bayes_stein", cov_method: str = "ledoit_wolf",
                 risk_free_rate: float = 0.02, constraints: Constraints | None = None,
                 fallback: str = "Equal weight") -> WeightFn:
    """Weight function that re-optimises on a trailing window at each call."""
    ppy = PERIODS_PER_YEAR[frequency]

    def fn(prices_so_far: pd.DataFrame) -> np.ndarray:
        cutoff = prices_so_far.index[-1] - pd.DateOffset(days=int(lookback_years * 365.25))
        window = prices_so_far.loc[cutoff:]
        rets = to_returns(window, frequency)
        n = prices_so_far.shape[1]
        if len(rets) < max(20, n + 2):
            return np.ones(n) / n
        mu = estimators.expected_returns(rets, ppy, return_method)
        cov = estimators.nearest_psd(estimators.covariance(rets, ppy, cov_method))
        try:
            opt = PortfolioOptimizer(mu, cov, risk_free_rate, constraints)
            try:
                return opt.by_name(strategy).weights.values
            except (InfeasibleError, RuntimeError):
                return opt.by_name(fallback).weights.values
        except (InfeasibleError, RuntimeError):
            return np.ones(n) / n

    return fn


def lookback_start(prices: pd.DataFrame, lookback_years: float) -> pd.Timestamp:
    """First date on which a walk-forward strategy has a full estimation window."""
    return prices.index[0] + pd.DateOffset(days=int(lookback_years * 365.25))
