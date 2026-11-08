import numpy as np
import pandas as pd
import pytest

from portfolio_optimizer.backtest import lookback_start, run_backtest, static_weights, walk_forward


def _prices():
    idx = pd.bdate_range("2020-01-01", periods=600)
    rng = np.random.default_rng(3)
    r = rng.normal([0.0004, 0.0001], [0.012, 0.004], size=(600, 2))
    return pd.DataFrame(100 * np.cumprod(1 + r, axis=0), index=idx, columns=["Eq", "Bd"])


def test_single_asset_buy_and_hold_tracks_price():
    p = _prices()
    res = run_backtest(p, static_weights(pd.Series({"Eq": 1.0, "Bd": 0.0})), "Eq", "Never", cost_bps=0)
    np.testing.assert_allclose(res.wealth.values, (p["Eq"] / p["Eq"].iloc[0]).values, rtol=1e-12)


def test_costs_and_fees_reduce_wealth():
    p = _prices()
    w = static_weights(pd.Series({"Eq": 0.6, "Bd": 0.4}))
    free = run_backtest(p, w, "free", "Monthly", cost_bps=0)
    costly = run_backtest(p, w, "costly", "Monthly", cost_bps=50, ter=pd.Series({"Eq": 0.01, "Bd": 0.01}))
    assert costly.wealth.iloc[-1] < free.wealth.iloc[-1]
    assert costly.costs_paid > 0


def test_rebalancing_restores_target():
    p = _prices()
    res = run_backtest(p, static_weights(pd.Series({"Eq": 0.5, "Bd": 0.5})), "50/50", "Quarterly", cost_bps=0)
    assert np.allclose(res.weights.values, 0.5)
    assert len(res.weights) > 5 and (res.turnover.iloc[1:] < 0.2).all()


def test_walk_forward_has_no_lookahead():
    p = _prices()
    seen = []

    def spy(prices_so_far):
        seen.append(prices_so_far.index[-1])
        return np.array([0.5, 0.5])

    res = run_backtest(p, spy, "spy", "Monthly", cost_bps=0)
    assert all(d in res.weights.index for d in seen)
    assert seen == sorted(seen)


def test_walk_forward_strategy_runs():
    p = _prices()
    fn = walk_forward("Minimum variance", lookback_years=1.0)
    res = run_backtest(p, fn, "gmv", "Quarterly", start=lookback_start(p, 1.0))
    assert res.weights["Bd"].mean() > 0.7      # low-vol asset dominates the GMV
    assert res.wealth.iloc[0] == pytest.approx(1 - 10 / 1e4)
