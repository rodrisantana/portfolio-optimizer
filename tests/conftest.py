import numpy as np
import pandas as pd
import pytest

from portfolio_optimizer.data import load_demo, to_returns


@pytest.fixture(scope="session")
def demo_prices() -> pd.DataFrame:
    return load_demo().prices


@pytest.fixture(scope="session")
def weekly_returns(demo_prices) -> pd.DataFrame:
    return to_returns(demo_prices, "weekly")


@pytest.fixture
def toy():
    """Three assets with a known covariance, used for closed-form checks."""
    assets = ["A", "B", "C"]
    vol = np.array([0.10, 0.20, 0.30])
    corr = np.array([[1.0, 0.3, 0.1], [0.3, 1.0, 0.5], [0.1, 0.5, 1.0]])
    cov = pd.DataFrame(np.outer(vol, vol) * corr, index=assets, columns=assets)
    mu = pd.Series([0.04, 0.08, 0.11], index=assets)
    return mu, cov
