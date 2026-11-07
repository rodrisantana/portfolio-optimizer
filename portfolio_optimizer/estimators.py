"""Estimators for the two inputs of mean-variance optimisation.

Sample means are the noisiest input in portfolio theory: with 7 years of data
the standard error of an equity ETF's mean return is about 6-7% a year, the
same size as the number itself. The optimiser then maximises estimation error.
Shrinkage estimators trade a little bias for a lot less variance, which is why
they are offered here and why Bayes-Stein / Ledoit-Wolf are sensible defaults.

All functions take periodic simple returns and return ANNUALISED quantities.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

RETURN_METHODS = ("historical", "ewma", "bayes_stein")
COV_METHODS = ("sample", "ledoit_wolf", "ewma")


# --------------------------------------------------------------------------- expected returns
def historical_mean(returns: pd.DataFrame, periods_per_year: int) -> pd.Series:
    return returns.mean() * periods_per_year


def ewma_mean(returns: pd.DataFrame, periods_per_year: int, halflife_years: float = 2.0) -> pd.Series:
    """Exponentially weighted mean: recent periods count more."""
    halflife = max(1.0, halflife_years * periods_per_year)
    return returns.ewm(halflife=halflife).mean().iloc[-1] * periods_per_year


def bayes_stein_mean(returns: pd.DataFrame, periods_per_year: int) -> tuple[pd.Series, float]:
    """Jorion (1986) Bayes-Stein estimator.

    Each mean is pulled towards the return of the global minimum-variance
    portfolio, which is estimated far more precisely than individual means:

        mu_BS = (1 - phi) * mu_hat + phi * mu_0 * 1
        phi   = (N + 2) / ((N + 2) + T (mu_hat - mu_0 1)' S^-1 (mu_hat - mu_0 1))

    Returns the annualised estimate and the shrinkage intensity phi.
    """
    x = returns.values
    t, n = x.shape
    mu = x.mean(axis=0)
    s = np.cov(x, rowvar=False, ddof=1)
    s_inv = np.linalg.pinv(s)
    ones = np.ones(n)
    w_gmv = s_inv @ ones / (ones @ s_inv @ ones)
    mu0 = float(w_gmv @ mu)
    d = mu - mu0
    phi = (n + 2) / ((n + 2) + t * float(d @ s_inv @ d))
    phi = float(np.clip(phi, 0.0, 1.0))
    shrunk = (1 - phi) * mu + phi * mu0
    return pd.Series(shrunk * periods_per_year, index=returns.columns), phi


def expected_returns(returns: pd.DataFrame, periods_per_year: int, method: str = "bayes_stein",
                     **kwargs) -> pd.Series:
    if method == "historical":
        return historical_mean(returns, periods_per_year)
    if method == "ewma":
        return ewma_mean(returns, periods_per_year, **kwargs)
    if method == "bayes_stein":
        return bayes_stein_mean(returns, periods_per_year)[0]
    raise ValueError(f"Unknown return method {method!r}; choose from {RETURN_METHODS}")


# --------------------------------------------------------------------------- covariance
def sample_cov(returns: pd.DataFrame, periods_per_year: int) -> pd.DataFrame:
    return returns.cov() * periods_per_year


def ledoit_wolf_cov(returns: pd.DataFrame, periods_per_year: int) -> tuple[pd.DataFrame, float]:
    """Ledoit & Wolf (2004) shrinkage towards the constant-correlation matrix.

    The target keeps every asset's own variance and replaces each correlation by
    the average correlation, so a bond ETF stays a low-volatility asset (a
    scaled-identity target would wrongly pull all variances to the average).
    The optimal intensity delta in [0, 1] is estimated from the data.

    Returns the annualised covariance and delta.
    """
    x = returns.values
    t, n = x.shape
    xc = x - x.mean(axis=0)
    s = xc.T @ xc / t                                  # MLE sample covariance
    var = np.diag(s)
    std = np.sqrt(var)
    corr = s / np.outer(std, std)
    r_bar = (corr.sum() - n) / (n * (n - 1)) if n > 1 else 0.0
    f = r_bar * np.outer(std, std)
    np.fill_diagonal(f, var)

    # pi_hat: sum of asymptotic variances of the sample covariance entries
    y = xc ** 2
    pi_mat = y.T @ y / t - s ** 2
    pi_hat = pi_mat.sum()

    # rho_hat: asymptotic covariance between the target and the sample
    term1 = (xc ** 3).T @ xc / t                       # E[x_i^3 x_j]
    term2 = var[:, None] * s                           # s_ii * s_ij
    theta = term1 - term2                              # theta_ii,ij
    np.fill_diagonal(theta, 0.0)
    ratio = std[None, :] / std[:, None]                # sqrt(s_jj / s_ii)
    rho_off = r_bar * (ratio * theta).sum()            # both (i,j) and (j,i) are summed
    rho_hat = np.trace(pi_mat) + rho_off

    gamma_hat = np.linalg.norm(s - f, "fro") ** 2
    kappa = (pi_hat - rho_hat) / gamma_hat if gamma_hat > 0 else 0.0
    delta = float(np.clip(kappa / t, 0.0, 1.0))
    sigma = delta * f + (1 - delta) * s
    return pd.DataFrame(sigma * periods_per_year, index=returns.columns, columns=returns.columns), delta


def ewma_cov(returns: pd.DataFrame, periods_per_year: int, halflife_years: float = 1.0) -> pd.DataFrame:
    """RiskMetrics-style exponentially weighted covariance."""
    halflife = max(1.0, halflife_years * periods_per_year)
    x = returns.values
    t = len(x)
    lam = 0.5 ** (1.0 / halflife)
    w = lam ** np.arange(t - 1, -1, -1)
    w /= w.sum()
    mu = w @ x
    xc = x - mu
    s = (xc * w[:, None]).T @ xc
    return pd.DataFrame(s * periods_per_year, index=returns.columns, columns=returns.columns)


def covariance(returns: pd.DataFrame, periods_per_year: int, method: str = "ledoit_wolf", **kwargs) -> pd.DataFrame:
    if method == "sample":
        return sample_cov(returns, periods_per_year)
    if method == "ledoit_wolf":
        return ledoit_wolf_cov(returns, periods_per_year)[0]
    if method == "ewma":
        return ewma_cov(returns, periods_per_year, **kwargs)
    raise ValueError(f"Unknown covariance method {method!r}; choose from {COV_METHODS}")


def nearest_psd(cov: pd.DataFrame, eps: float = 1e-10) -> pd.DataFrame:
    """Clip negative eigenvalues so user-edited or EWMA matrices stay valid."""
    vals, vecs = np.linalg.eigh(cov.values)
    vals = np.maximum(vals, eps)
    fixed = vecs @ np.diag(vals) @ vecs.T
    fixed = (fixed + fixed.T) / 2
    return pd.DataFrame(fixed, index=cov.index, columns=cov.columns)


def cov_to_corr(cov: pd.DataFrame) -> pd.DataFrame:
    std = np.sqrt(np.diag(cov.values))
    corr = cov.values / np.outer(std, std)
    return pd.DataFrame(corr, index=cov.index, columns=cov.columns)


def mean_standard_error(returns: pd.DataFrame, periods_per_year: int) -> pd.Series:
    """Annualised standard error of the sample mean: how unsure we are of mu."""
    return returns.std() / np.sqrt(len(returns)) * periods_per_year
