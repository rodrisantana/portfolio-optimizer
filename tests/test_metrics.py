import numpy as np
import pandas as pd
import pytest

from portfolio_optimizer import metrics as M


def test_drawdown_and_cagr():
    idx = pd.to_datetime(["2020-01-01", "2021-01-01", "2022-01-01", "2023-01-01"])
    w = pd.Series([100.0, 120.0, 90.0, 121.0], index=idx)
    assert M.max_drawdown(w) == pytest.approx(-0.25)
    years = (idx[-1] - idx[0]).days / 365.25
    assert M.cagr(w) == pytest.approx(1.21 ** (1 / years) - 1)
    assert M.longest_drawdown_days(w) == (idx[3] - idx[2]).days + (idx[2] - idx[1]).days


def test_summary_constant_returns():
    r = pd.Series(0.01, index=pd.date_range("2020-01-31", periods=24, freq="ME"))
    s = M.summary(r, 12, 0.0)
    assert s["Volatility"] == pytest.approx(0.0)
    assert s["Max drawdown"] == 0.0
    assert s["Positive periods"] == 1.0


def test_var_cvar_ordering():
    r = pd.Series(np.random.default_rng(0).normal(0, 0.02, 5000))
    assert M.historical_cvar(r) > M.historical_var(r) > 0
    assert M.historical_var(r) == pytest.approx(1.645 * 0.02, rel=0.08)


def test_beta_against_itself_is_one():
    r = pd.Series(np.random.default_rng(1).normal(0, 0.01, 300), index=pd.bdate_range("2024-01-01", periods=300))
    s = M.summary(r, 252, benchmark=r)
    assert s["Beta"] == pytest.approx(1.0) and s["Tracking error"] == pytest.approx(0.0)


def test_calendar_year_returns():
    idx = pd.to_datetime(["2020-06-30", "2020-12-31", "2021-12-31"])
    w = pd.Series([100.0, 110.0, 99.0], index=idx)
    y = M.calendar_year_returns(w)
    assert y.iloc[0, 0] == pytest.approx(0.10) and y.iloc[1, 0] == pytest.approx(-0.10)
