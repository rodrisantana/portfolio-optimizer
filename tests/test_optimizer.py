import numpy as np
import pandas as pd
import pytest

from portfolio_optimizer.optimizer import (
    Constraints,
    GroupLimit,
    InfeasibleError,
    PortfolioOptimizer,
    diversification_ratio,
    effective_n,
    risk_contributions,
)


def test_unconstrained_gmv_matches_closed_form(toy):
    mu, cov = toy
    inv = np.linalg.inv(cov.values)
    w_closed = inv @ np.ones(3) / (np.ones(3) @ inv @ np.ones(3))
    assert (w_closed > 0).all()            # interior solution, so long-only bounds are inactive
    w = PortfolioOptimizer(mu, cov).min_variance().weights.values
    np.testing.assert_allclose(w, w_closed, atol=1e-6)


def test_tangency_matches_closed_form_when_interior(toy):
    mu, cov = toy
    rf = 0.01
    inv = np.linalg.inv(cov.values)
    z = inv @ (mu.values - rf)
    w_closed = z / z.sum()
    assert (w_closed > 0).all()
    p = PortfolioOptimizer(mu, cov, rf).max_sharpe()
    np.testing.assert_allclose(p.weights.values, w_closed, atol=1e-5)


def test_max_sharpe_beats_every_frontier_point(weekly_returns):
    from portfolio_optimizer import estimators as E
    mu = E.historical_mean(weekly_returns, 52)
    cov = E.ledoit_wolf_cov(weekly_returns, 52)[0]
    opt = PortfolioOptimizer(mu, cov, 0.02)
    best = opt.max_sharpe().sharpe
    frontier = opt.efficient_frontier(40)
    assert best >= max(p.sharpe for p in frontier) - 1e-6
    gmv = opt.min_variance()
    assert gmv.volatility <= min(p.volatility for p in frontier) + 1e-9
    # frontier is increasing in both return and risk
    rets = [p.expected_return for p in frontier]
    vols = [p.volatility for p in frontier]
    assert np.all(np.diff(rets) > -1e-9) and np.all(np.diff(vols) > -1e-7)


def test_max_sharpe_respects_bounds_and_groups(weekly_returns):
    from portfolio_optimizer import estimators as E
    mu = E.historical_mean(weekly_returns, 52)
    cov = E.sample_cov(weekly_returns, 52)
    cons = Constraints(default_upper=0.35, groups=[GroupLimit("Bonds", ["SXRQ.DE", "IBCI.DE"], 0.20, 0.40)])
    opt = PortfolioOptimizer(mu, cov, 0.02, cons)
    for p in (opt.max_sharpe(), opt.min_variance(), opt.max_diversification(), opt.efficient_risk(0.10)):
        w = p.weights
        assert abs(w.sum() - 1) < 1e-8
        assert (w >= -1e-9).all() and (w <= 0.35 + 1e-6).all(), p.name
        bonds = w["SXRQ.DE"] + w["IBCI.DE"]
        assert 0.20 - 1e-6 <= bonds <= 0.40 + 1e-6, p.name


def test_max_sharpe_is_global_vs_random_search(toy):
    mu, cov = toy
    cons = Constraints(default_upper=0.6)
    opt = PortfolioOptimizer(mu, cov, 0.02, cons)
    best = opt.max_sharpe().sharpe
    rng = np.random.default_rng(0)
    w = rng.dirichlet(np.ones(3), 20000)
    w = w[(w <= 0.6).all(axis=1)]
    s = (w @ mu.values - 0.02) / np.sqrt(np.einsum("ij,jk,ik->i", w, cov.values, w))
    assert best >= s.max() - 1e-9


def test_efficient_risk_hits_target(toy):
    mu, cov = toy
    opt = PortfolioOptimizer(mu, cov)
    p = opt.efficient_risk(0.15)
    assert p.volatility == pytest.approx(0.15, abs=1e-5)
    with pytest.raises(InfeasibleError):
        opt.efficient_risk(0.01)


def test_risk_parity_equalises_contributions(weekly_returns):
    from portfolio_optimizer import estimators as E
    cov = E.ledoit_wolf_cov(weekly_returns, 52)[0]
    mu = pd.Series(0.05, index=cov.index)
    p = PortfolioOptimizer(mu, cov).risk_parity()
    rc = risk_contributions(p.weights, cov)
    np.testing.assert_allclose(rc.values, 1 / len(rc), atol=1e-6)


def test_hrp_is_long_only_and_sums_to_one(toy):
    mu, cov = toy
    w = PortfolioOptimizer(mu, cov).hierarchical_risk_parity().weights
    assert abs(w.sum() - 1) < 1e-12 and (w > 0).all()
    assert w["A"] > w["C"]                  # lowest-vol asset gets the most weight


def test_infeasible_constraints_are_reported(toy):
    mu, cov = toy
    with pytest.raises(InfeasibleError):
        PortfolioOptimizer(mu, cov, constraints=Constraints(default_upper=0.3))
    with pytest.raises(InfeasibleError):
        PortfolioOptimizer(mu, cov, constraints=Constraints(lower={"A": 0.6, "B": 0.6}))


def test_tangency_needs_positive_excess(toy):
    mu, cov = toy
    with pytest.raises(InfeasibleError):
        PortfolioOptimizer(mu, cov, risk_free_rate=0.5).max_sharpe()


def test_analytics(toy):
    mu, cov = toy
    w = pd.Series([1 / 3] * 3, index=mu.index)
    assert risk_contributions(w, cov).sum() == pytest.approx(1.0)
    assert effective_n(w) == pytest.approx(3.0)
    assert diversification_ratio(w, cov) > 1.0
