"""Monte Carlo projection of a portfolio with contributions or withdrawals.

Monthly steps. For each simulated path

    V_{t+1} = max(0, V_t * (1 + r_t - fee/12) + C_t)

where C_t is the monthly contribution (negative for withdrawals), optionally
indexed every year. Three return generators are available:

* ``lognormal``: i.i.d. log-normal returns whose annual mean and volatility
  match the inputs exactly (moment matching, not the naive mu - sigma^2/2 guess).
* ``student_t``: same mean and volatility, fat tails (crashes are more frequent).
* ``bootstrap``: resamples blocks of 12 real historical months, so it keeps
  fat tails, skew and short-term momentum of the actual data. The sample can
  be re-centred on the assumed mean, because 2019-2026 equity returns were far
  above any reasonable forward-looking estimate.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

METHODS = ("lognormal", "student_t", "bootstrap")
PERCENTILES = (5, 25, 50, 75, 95)


@dataclass
class SimulationInput:
    initial: float = 10_000.0
    monthly_contribution: float = 300.0
    contribution_growth: float = 0.0          # yearly indexation of the contribution
    years: int = 20
    expected_return: float = 0.06             # annual arithmetic mean, before fees
    volatility: float = 0.15
    annual_fee: float = 0.002                 # TER / platform fee
    inflation: float = 0.02
    method: str = "lognormal"
    df: float = 5.0                           # Student-t degrees of freedom
    n_sims: int = 5000
    seed: int | None = 42
    target: float | None = None               # goal in today's money
    recenter_bootstrap: bool = True


@dataclass
class SimulationResult:
    inputs: SimulationInput
    months: pd.DatetimeIndex
    paths: np.ndarray                         # nominal values, shape (n_sims, n_months + 1)
    contributed: np.ndarray                   # cumulative net contributions (incl. initial)
    deflator: np.ndarray                      # divide nominal by this to get today's money
    returns: np.ndarray                       # simulated monthly returns net of fees, (n_sims, n_months)

    def percentiles(self, real: bool = False) -> pd.DataFrame:
        vals = self.paths / self.deflator if real else self.paths
        q = np.percentile(vals, PERCENTILES, axis=0)
        return pd.DataFrame(q.T, index=self.months, columns=[f"P{p}" for p in PERCENTILES])

    def final(self, real: bool = False) -> np.ndarray:
        return self.paths[:, -1] / (self.deflator[-1] if real else 1.0)

    def prob_reaching(self, target: float, real: bool = True) -> float:
        return float((self.final(real) >= target).mean())

    @property
    def prob_ruin(self) -> float:
        """Share of paths whose value hits zero (only possible with withdrawals)."""
        return float((self.paths[:, 1:] <= 0).any(axis=1).mean())

    def prob_loss(self) -> float:
        """Share of paths that end below the money put in (nominal)."""
        return float((self.paths[:, -1] < self.contributed[-1]).mean())

    def max_drawdowns(self) -> np.ndarray:
        """Worst peak-to-trough fall of each path's investment return.

        Measured on a unit-value index of returns so contributions do not hide
        the fall.
        """
        idx = np.cumprod(1.0 + self.returns, axis=1)
        peak = np.maximum.accumulate(idx, axis=1)
        return (idx / peak - 1.0).min(axis=1)

    def summary(self) -> dict[str, float]:
        fin_nom, fin_real = self.final(), self.final(real=True)
        out = {
            "Median final value": float(np.median(fin_nom)),
            "Median final value (today's money)": float(np.median(fin_real)),
            "Pessimistic (P5, today's money)": float(np.percentile(fin_real, 5)),
            "Optimistic (P95, today's money)": float(np.percentile(fin_real, 95)),
            "Total contributed": float(self.contributed[-1]),
            "Probability of ending below contributions": self.prob_loss(),
            "Probability of ruin": self.prob_ruin,
            "Median worst drawdown": float(np.median(self.max_drawdowns())),
        }
        if self.inputs.target:
            out["Probability of reaching the goal"] = self.prob_reaching(self.inputs.target)
        return out


def lognormal_params(mean: float, vol: float) -> tuple[float, float]:
    """Annual log-return mean m and std s such that E[1+R] = 1+mean, Std[1+R] = vol."""
    if mean <= -1:
        raise ValueError("Expected return must be above -100%.")
    s2 = np.log1p((vol / (1.0 + mean)) ** 2)
    m = np.log1p(mean) - 0.5 * s2
    return float(m), float(np.sqrt(s2))


def _monthly_returns(inp: SimulationInput, n_months: int, rng: np.random.Generator,
                     history: pd.Series | None) -> np.ndarray:
    shape = (inp.n_sims, n_months)
    m, s = lognormal_params(inp.expected_return, inp.volatility)
    mm, sm = m / 12.0, s / np.sqrt(12.0)
    if inp.method == "lognormal":
        return np.expm1(mm + sm * rng.standard_normal(shape))
    if inp.method == "student_t":
        if inp.df <= 2:
            raise ValueError("Student-t needs more than 2 degrees of freedom for a finite variance.")
        z = rng.standard_t(inp.df, size=shape) * np.sqrt((inp.df - 2) / inp.df)
        z = np.clip(z, -10, 10)          # keeps E[exp(X)] finite; affects < 1e-6 of draws
        gross = np.exp(mm + sm * z)
        # rescale so the mean monthly growth matches the log-normal case exactly
        gross *= (1 + inp.expected_return) ** (1 / 12) / gross.mean()
        return gross - 1.0
    if inp.method == "bootstrap":
        if history is None or len(history) < 24:
            raise ValueError("Bootstrap needs at least 24 months of history.")
        h = history.dropna().values.astype(float)
        if inp.recenter_bootstrap:
            target_monthly = (1 + inp.expected_return) ** (1 / 12) - 1
            h = h - h.mean() + target_monthly
        block = 12
        n_blocks = int(np.ceil(n_months / block))
        starts = rng.integers(0, len(h) - block + 1, size=(inp.n_sims, n_blocks))
        idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(inp.n_sims, -1)[:, :n_months]
        return h[idx]
    raise ValueError(f"Unknown method {inp.method!r}; choose from {METHODS}")


def simulate(inp: SimulationInput, history: pd.Series | None = None,
             start: pd.Timestamp | None = None) -> SimulationResult:
    """Run the projection. ``history`` (monthly simple returns) is only used by the bootstrap."""
    if inp.years <= 0 or inp.n_sims <= 0:
        raise ValueError("Horizon and number of simulations must be positive.")
    rng = np.random.default_rng(inp.seed)
    n_months = int(inp.years * 12)
    rets = _monthly_returns(inp, n_months, rng, history) - inp.annual_fee / 12.0

    contrib = inp.monthly_contribution * (1 + inp.contribution_growth) ** (np.arange(n_months) // 12)
    paths = np.empty((inp.n_sims, n_months + 1))
    paths[:, 0] = inp.initial
    for t in range(n_months):
        paths[:, t + 1] = np.maximum(paths[:, t] * (1.0 + rets[:, t]) + contrib[t], 0.0)

    contributed = np.concatenate([[inp.initial], inp.initial + np.cumsum(contrib)])
    deflator = (1 + inp.inflation) ** (np.arange(n_months + 1) / 12.0)
    start = pd.Timestamp.today().normalize() if start is None else pd.Timestamp(start)
    months = pd.date_range(start, periods=n_months + 1, freq="MS")
    return SimulationResult(inp, months, paths, contributed, deflator, rets)


def required_contribution(inp: SimulationInput, target: float, confidence: float = 0.5,
                          history: pd.Series | None = None, tol: float = 1.0) -> float:
    """Monthly contribution needed to reach ``target`` (today's money) with the given probability.

    Bisection on the contribution with common random numbers (same seed), so
    the success probability is monotone in the contribution.
    """
    lo, hi = 0.0, max(1000.0, target / max(inp.years * 12, 1))
    def ok(c: float) -> bool:
        trial = SimulationInput(**{**inp.__dict__, "monthly_contribution": c, "n_sims": min(inp.n_sims, 3000)})
        return simulate(trial, history).prob_reaching(target) >= confidence
    if ok(lo):
        return 0.0
    while not ok(hi):
        hi *= 2
        if hi > 1e7:
            return float("inf")
    while hi - lo > tol:
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if ok(mid) else (mid, hi)
    return hi


def horizon_table(sim: SimulationResult, horizons: list[int] | None = None, real: bool = True) -> pd.DataFrame:
    """Return and money at several horizons.

    The annualised return of each path over the first ``h`` years (investment
    return only, contributions excluded) shows how uncertainty shrinks with
    time; the money columns include contributions.
    """
    years = sim.returns.shape[1] // 12
    horizons = horizons or [h for h in (1, 3, 5, 10, 15, 20, 25, 30, 40, 50) if h <= years]
    if years not in horizons:
        horizons = sorted(set(horizons) | {years})
    rows = []
    log_growth = np.cumsum(np.log1p(sim.returns), axis=1)
    for h in horizons:
        m = 12 * h
        ann = np.expm1(log_growth[:, m - 1] / h)
        vals = sim.paths[:, m] / (sim.deflator[m] if real else 1.0)
        contributed = sim.contributed[m] / (sim.deflator[m] if real else 1.0)
        q = np.percentile(ann, [10, 25, 50, 75, 90])
        v = np.percentile(vals, [10, 50, 90])
        rows.append({"Years": h, "Return P10": q[0], "Return P25": q[1], "Return P50": q[2], "Return P75": q[3],
                     "Return P90": q[4], "Probability of a loss": float((ann < 0).mean()),
                     "Contributed": contributed, "Money P10": v[0], "Money P50": v[1], "Money P90": v[2]})
    return pd.DataFrame(rows).set_index("Years")
