"""Performance and risk statistics for return or wealth series."""

from __future__ import annotations

import numpy as np
import pandas as pd


def wealth_from_returns(returns: pd.Series, start: float = 1.0) -> pd.Series:
    return start * (1.0 + returns).cumprod()


def drawdown(wealth: pd.Series) -> pd.Series:
    """Percentage below the running peak (0 at a new high, negative otherwise)."""
    return wealth / wealth.cummax() - 1.0


def max_drawdown(wealth: pd.Series) -> float:
    return float(drawdown(wealth).min())


def longest_drawdown_days(wealth: pd.Series) -> int:
    """Calendar days of the longest peak-to-recovery spell (an open spell counts up to the last date)."""
    longest, peak_value, peak_date, underwater = 0, -np.inf, None, False
    for date, value in wealth.items():
        if value >= peak_value:
            if underwater:
                longest = max(longest, (date - peak_date).days)
            peak_value, peak_date, underwater = value, date, False
        else:
            underwater = True
    if underwater:
        longest = max(longest, (wealth.index[-1] - peak_date).days)
    return int(longest)


def cagr(wealth: pd.Series) -> float:
    years = (wealth.index[-1] - wealth.index[0]).days / 365.25
    if years <= 0 or wealth.iloc[0] <= 0:
        return 0.0
    return float((wealth.iloc[-1] / wealth.iloc[0]) ** (1 / years) - 1)


def historical_var(returns: pd.Series, level: float = 0.95) -> float:
    """Loss threshold exceeded in (1 - level) of periods, reported as a positive number."""
    return float(-np.quantile(returns, 1 - level))


def historical_cvar(returns: pd.Series, level: float = 0.95) -> float:
    """Expected shortfall: average loss in the worst (1 - level) of periods."""
    cut = np.quantile(returns, 1 - level)
    tail = returns[returns <= cut]
    return float(-tail.mean()) if len(tail) else 0.0


def summary(returns: pd.Series, periods_per_year: int, risk_free_rate: float = 0.0,
            benchmark: pd.Series | None = None) -> dict[str, float]:
    """Headline statistics of one return series.

    Sharpe and Sortino use the annual risk-free rate converted to the period.
    """
    r = returns.dropna()
    wealth = wealth_from_returns(r)
    rf_p = (1 + risk_free_rate) ** (1 / periods_per_year) - 1
    excess = r - rf_p
    vol = float(r.std() * np.sqrt(periods_per_year))
    downside = np.sqrt(np.mean(np.minimum(excess, 0.0) ** 2)) * np.sqrt(periods_per_year)
    growth = cagr(wealth)
    mdd = max_drawdown(wealth)
    out = {
        "CAGR": growth,
        "Volatility": vol,
        "Sharpe": float(excess.mean() * periods_per_year / vol) if vol > 0 else 0.0,
        "Sortino": float(excess.mean() * periods_per_year / downside) if downside > 0 else 0.0,
        "Max drawdown": mdd,
        "Calmar": growth / abs(mdd) if mdd < 0 else 0.0,
        "VaR 95%": historical_var(r),
        "CVaR 95%": historical_cvar(r),
        "Best period": float(r.max()),
        "Worst period": float(r.min()),
        "Positive periods": float((r > 0).mean()),
        "Longest drawdown (days)": float(longest_drawdown_days(wealth)),
    }
    if benchmark is not None:
        b = benchmark.reindex(r.index).dropna()
        rr = r.reindex(b.index)
        if len(b) > 2 and b.var() > 0:
            beta = float(np.cov(rr, b, ddof=1)[0, 1] / b.var())
            active = rr - b
            te = float(active.std() * np.sqrt(periods_per_year))
            out.update({
                "Beta": beta,
                "Correlation": float(rr.corr(b)),
                "Tracking error": te,
                "Information ratio": float(active.mean() * periods_per_year / te) if te > 0 else 0.0,
            })
    return out


def summary_table(returns: pd.DataFrame, periods_per_year: int, risk_free_rate: float = 0.0,
                  benchmark: pd.Series | None = None) -> pd.DataFrame:
    rows = {c: summary(returns[c], periods_per_year, risk_free_rate, benchmark) for c in returns.columns}
    return pd.DataFrame(rows).T


def calendar_year_returns(wealth: pd.DataFrame | pd.Series) -> pd.DataFrame:
    """Return per calendar year (the first year is partial if the data starts mid-year)."""
    frame = wealth.to_frame() if isinstance(wealth, pd.Series) else wealth
    year_end = frame.groupby(frame.index.year).last()
    first = frame.iloc[[0]]
    first.index = [frame.index[0].year - 1]
    stacked = pd.concat([first, year_end])
    out = stacked.pct_change().iloc[1:]
    out.index.name = "Year"
    return out


def rolling_volatility(returns: pd.Series, window: int, periods_per_year: int) -> pd.Series:
    return returns.rolling(window).std() * np.sqrt(periods_per_year)
