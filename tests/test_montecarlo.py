import numpy as np
import pandas as pd
import pytest

from portfolio_optimizer.montecarlo import SimulationInput, lognormal_params, required_contribution, simulate


def test_lognormal_moment_matching():
    m, s = lognormal_params(0.07, 0.16)
    rng = np.random.default_rng(0)
    gross = np.exp(m + s * rng.standard_normal(2_000_000))
    assert gross.mean() - 1 == pytest.approx(0.07, abs=1e-3)
    assert gross.std() == pytest.approx(0.16, abs=1e-3)


def test_zero_volatility_is_deterministic():
    inp = SimulationInput(initial=1000, monthly_contribution=0, years=10, expected_return=0.05, volatility=0.0,
                          annual_fee=0.0, n_sims=50)
    res = simulate(inp)
    assert res.final() == pytest.approx(np.full(50, 1000 * 1.05 ** 10), rel=1e-9)


@pytest.mark.parametrize("method", ["lognormal", "student_t"])
def test_simulated_mean_growth(method):
    inp = SimulationInput(initial=1000, monthly_contribution=0, years=5, expected_return=0.06, volatility=0.15,
                          annual_fee=0.0, n_sims=40000, method=method, seed=1)
    res = simulate(inp)
    assert res.final().mean() == pytest.approx(1000 * 1.06 ** 5, rel=0.02)


def test_contributions_and_inflation():
    inp = SimulationInput(initial=0, monthly_contribution=100, years=2, expected_return=0.0, volatility=0.0,
                          annual_fee=0.0, inflation=0.02, n_sims=10)
    res = simulate(inp)
    assert res.contributed[-1] == pytest.approx(2400)
    assert res.final().mean() == pytest.approx(2400)
    assert res.final(real=True).mean() == pytest.approx(2400 / 1.02 ** 2)
    assert res.prob_ruin == 0.0


def test_withdrawals_can_ruin():
    inp = SimulationInput(initial=10_000, monthly_contribution=-500, years=5, expected_return=0.0, volatility=0.1,
                          n_sims=500)
    res = simulate(inp)
    assert res.prob_ruin > 0.9
    assert (res.paths >= 0).all()


def test_bootstrap_recentering():
    hist = pd.Series(np.random.default_rng(2).normal(0.02, 0.04, 120))
    inp = SimulationInput(initial=1000, monthly_contribution=0, years=10, expected_return=0.05,
                          method="bootstrap", n_sims=20000, annual_fee=0.0)
    res = simulate(inp, history=hist)
    annual = res.returns.mean() * 12
    assert annual == pytest.approx(12 * (1.05 ** (1 / 12) - 1), abs=0.003)


def test_required_contribution_monotone():
    inp = SimulationInput(initial=0, years=10, expected_return=0.05, volatility=0.1, n_sims=2000, inflation=0.0,
                          annual_fee=0.0)
    c50 = required_contribution(inp, 50_000, 0.5)
    c90 = required_contribution(inp, 50_000, 0.9)
    assert 0 < c50 < c90 < 50_000 / 120


def test_horizon_table_narrows_with_time():
    from portfolio_optimizer.montecarlo import horizon_table
    inp = SimulationInput(initial=10_000, monthly_contribution=100, years=20, expected_return=0.06,
                          volatility=0.15, annual_fee=0.0, n_sims=4000)
    tab = horizon_table(simulate(inp), real=False)
    spread = tab["Return P90"] - tab["Return P10"]
    assert spread.is_monotonic_decreasing
    assert tab.loc[20, "Return P50"] == pytest.approx(0.06 - 0.15 ** 2 / 2, abs=0.01)
    assert tab["Probability of a loss"].iloc[0] > tab["Probability of a loss"].iloc[-1]
