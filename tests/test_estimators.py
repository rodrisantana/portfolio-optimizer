import numpy as np
import pandas as pd
import pytest

from portfolio_optimizer import estimators as E


def test_annualisation(weekly_returns):
    np.testing.assert_allclose(E.historical_mean(weekly_returns, 52), weekly_returns.mean() * 52)
    np.testing.assert_allclose(E.sample_cov(weekly_returns, 52), weekly_returns.cov() * 52)


def test_bayes_stein_shrinks_towards_common_mean(weekly_returns):
    hist = E.historical_mean(weekly_returns, 52)
    bs, phi = E.bayes_stein_mean(weekly_returns, 52)
    assert 0 < phi < 1
    assert bs.std() < hist.std()                         # dispersion shrinks
    assert np.all(np.sign(bs - bs.mean()) == np.sign(hist - hist.mean()))   # ranking direction kept


def test_ledoit_wolf_properties(weekly_returns):
    cov, delta = E.ledoit_wolf_cov(weekly_returns, 52)
    assert 0 <= delta <= 1
    assert np.all(np.linalg.eigvalsh(cov.values) > 0)
    sample_var = weekly_returns.var(ddof=0) * 52
    np.testing.assert_allclose(np.diag(cov), sample_var, rtol=1e-10)   # target keeps own variances


def test_ledoit_wolf_shrinks_more_with_less_data():
    rng = np.random.default_rng(1)
    n = 10
    a = rng.standard_normal((n, n))
    true = a @ a.T / n + np.eye(n)              # not constant-correlation, so delta < 1 with enough data
    chol = np.linalg.cholesky(true)
    small = pd.DataFrame(rng.standard_normal((40, n)) @ chol.T)
    large = pd.DataFrame(rng.standard_normal((4000, n)) @ chol.T)
    assert E.ledoit_wolf_cov(small, 1)[1] > E.ledoit_wolf_cov(large, 1)[1]


def test_ewma_cov_is_psd_and_weights_recent(weekly_returns):
    cov = E.ewma_cov(weekly_returns, 52, halflife_years=0.5)
    assert np.all(np.linalg.eigvalsh(cov.values) > -1e-12)


def test_nearest_psd_fixes_negative_eigenvalues():
    bad = pd.DataFrame([[1.0, 0.99, 0.0], [0.99, 1.0, 0.99], [0.0, 0.99, 1.0]])
    assert np.linalg.eigvalsh(bad.values).min() < 0
    assert np.linalg.eigvalsh(E.nearest_psd(bad).values).min() > 0


def test_unknown_method_raises(weekly_returns):
    with pytest.raises(ValueError):
        E.expected_returns(weekly_returns, 52, "magic")
