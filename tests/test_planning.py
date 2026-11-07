import numpy as np
import pandas as pd
import pytest

from portfolio_optimizer.assumptions import DEFAULT_CMA, long_term_returns
from portfolio_optimizer.breakdown import breakdown
from portfolio_optimizer.catalog import get
from portfolio_optimizer.planning import historical_dca, projection_table, xirr


def test_projection_matches_annuity_formula():
    r, years, m = 0.06, 10, 200.0
    tab = projection_table(1000, m, years, r)
    rm = 1.06 ** (1 / 12) - 1
    n = years * 12
    expected = 1000 * (1 + rm) ** n + m * ((1 + rm) ** n - 1) / rm
    assert tab["Value"].iloc[-1] == pytest.approx(expected)
    assert tab["Contributed"].iloc[-1] == pytest.approx(1000 + m * n)


def test_xirr_simple():
    idx = pd.to_datetime(["2020-01-01", "2021-01-01"])
    assert xirr(pd.Series([-100.0, 110.0], index=idx)) == pytest.approx(0.10, abs=1e-3)


def test_historical_dca_constant_growth():
    idx = pd.bdate_range("2020-01-01", "2024-12-31")
    years = np.array([(d - idx[0]).days / 365.25 for d in idx])
    wealth = pd.Series(1.08 ** years, index=idx)
    path, irr = historical_dca(wealth, 100.0, 1000.0)
    assert irr == pytest.approx(0.08, abs=2e-3)
    assert path["Contributed"].iloc[-1] == pytest.approx(1000 + 100 * 59)


def test_long_term_returns_net_of_fees_and_lookthrough():
    insts = {k: get(k) for k in ("EUNL.DE", "ES0119199000", "FR0010135103", "IS3N.DE")}
    lt = long_term_returns(insts)
    assert lt["EUNL.DE"] == pytest.approx(DEFAULT_CMA["Equity · Global"] - 0.0020)
    assert lt["IS3N.DE"] == pytest.approx(DEFAULT_CMA["Equity · Emerging"] - 0.0018)
    premium = DEFAULT_CMA["Equity · small cap / value premium"]
    assert lt["ES0119199000"] == pytest.approx(DEFAULT_CMA["Equity · Global"] + premium - 0.018)
    carm = 0.4 * DEFAULT_CMA["Equity · Global"] + 0.6 * DEFAULT_CMA["Fixed income · Aggregate"] - 0.015
    assert lt["FR0010135103"] == pytest.approx(carm)
    assert long_term_returns(insts, active_alpha=0.01)["ES0119199000"] == pytest.approx(lt["ES0119199000"] + 0.01)


def test_breakdown_dimensions():
    insts = {k: get(k) for k in ("EUNL.DE", "FR0010135103", "4GLD.DE", "ES0119199000")}
    w = pd.Series({"EUNL.DE": 0.4, "FR0010135103": 0.3, "4GLD.DE": 0.1, "ES0119199000": 0.2})
    ac = breakdown(w, insts, "Asset class")
    assert ac["Equity"] == pytest.approx(0.4 + 0.12 + 0.2)
    assert ac["Fixed income"] == pytest.approx(0.18)
    assert ac.sum() == pytest.approx(1.0)
    mg = breakdown(w, insts, "Management")
    assert mg["Active"] == pytest.approx(0.5) and mg["Passive"] == pytest.approx(0.5)
    vh = breakdown(w, insts, "Vehicle")
    assert vh["ETC"] == pytest.approx(0.1) and vh["Active fund"] == pytest.approx(0.5)
    assert breakdown(w, insts, "Region").sum() == pytest.approx(1.0)


def test_group_limit_uses_exposure(toy):
    from portfolio_optimizer.optimizer import Constraints, GroupLimit, PortfolioOptimizer
    mu, cov = toy
    g = GroupLimit("Equity", ["A", "B", "C"], 0.0, 0.5, exposure={"A": 0.0, "B": 1.0, "C": 0.5})
    p = PortfolioOptimizer(mu, cov, 0.0, Constraints(groups=[g])).max_sharpe()
    assert p.weights["B"] + 0.5 * p.weights["C"] <= 0.5 + 1e-6


def test_median_growth_below_mean():
    from portfolio_optimizer.assumptions import median_growth
    assert median_growth(0.07, 0.0) == pytest.approx(0.07)
    assert median_growth(0.07, 0.15) == pytest.approx(0.07 - 0.15 ** 2 / 2, abs=0.003)
