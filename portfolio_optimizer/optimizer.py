"""Portfolio construction: mean-variance and risk-based allocations.

Conventions
-----------
* ``mu`` and ``cov`` are annualised; weights sum to one; no leverage.
* Per-asset bounds and group (asset-class) limits apply to every
  mean-variance method. Risk parity and HRP are defined without constraints
  and ignore them (their weights are always long-only by construction).
* Each convex problem is solved with SLSQP using analytic gradients. Being
  convex, a local optimum is the global optimum, so one start is enough.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import leaves_list, linkage
from scipy.optimize import linprog, minimize
from scipy.spatial.distance import squareform

_TOL = 1e-9

STRATEGIES = ("Maximum Sharpe", "Minimum variance", "Maximum diversification", "Risk parity", "HRP",
              "Inverse volatility", "Equal weight")
# Strategies that honour per-asset and group constraints.
CONSTRAINED = {"Maximum Sharpe", "Minimum variance", "Maximum diversification"}


@dataclass
class GroupLimit:
    name: str
    members: list[str]
    lower: float = 0.0
    upper: float = 1.0


@dataclass
class Constraints:
    """Long-only box constraints plus optional group limits."""

    lower: dict[str, float] = field(default_factory=dict)
    upper: dict[str, float] = field(default_factory=dict)
    groups: list[GroupLimit] = field(default_factory=list)
    default_upper: float = 1.0

    def bounds(self, assets: list[str]) -> tuple[np.ndarray, np.ndarray]:
        lo = np.array([max(0.0, self.lower.get(a, 0.0)) for a in assets])
        hi = np.array([min(1.0, self.upper.get(a, self.default_upper)) for a in assets])
        return lo, hi

    def group_matrix(self, assets: list[str]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        if not self.groups:
            return np.zeros((0, len(assets))), np.zeros(0), np.zeros(0)
        a = np.array([[1.0 if x in g.members else 0.0 for x in assets] for g in self.groups])
        return a, np.array([g.lower for g in self.groups]), np.array([g.upper for g in self.groups])


@dataclass
class Portfolio:
    name: str
    weights: pd.Series
    expected_return: float
    volatility: float
    sharpe: float

    def as_row(self) -> dict:
        return {"Portfolio": self.name, "Return": self.expected_return,
                "Volatility": self.volatility, "Sharpe": self.sharpe}


class InfeasibleError(ValueError):
    pass


class PortfolioOptimizer:
    def __init__(self, mu: pd.Series, cov: pd.DataFrame, risk_free_rate: float = 0.02,
                 constraints: Constraints | None = None):
        if list(mu.index) != list(cov.index) or list(cov.index) != list(cov.columns):
            raise ValueError("mu and cov must share the same asset order.")
        self.assets = list(mu.index)
        self.n = len(self.assets)
        self.mu = mu.values.astype(float)
        self.cov = cov.values.astype(float)
        self.rf = float(risk_free_rate)
        self.constraints = constraints or Constraints()
        self.lo, self.hi = self.constraints.bounds(self.assets)
        self.g_mat, self.g_lo, self.g_hi = self.constraints.group_matrix(self.assets)
        self._check_feasible()

    # ------------------------------------------------------------------ helpers
    def evaluate(self, weights, name: str = "Custom") -> Portfolio:
        w = np.asarray(weights, dtype=float)
        ret = float(w @ self.mu)
        vol = float(np.sqrt(max(w @ self.cov @ w, 0.0)))
        sharpe = (ret - self.rf) / vol if vol > 0 else 0.0
        return Portfolio(name, pd.Series(w, index=self.assets), ret, vol, sharpe)

    def _clean(self, w: np.ndarray) -> np.ndarray:
        w = np.clip(w, self.lo, self.hi)
        w[np.abs(w) < 1e-7] = 0.0
        return w / w.sum()

    def _linear_constraints(self) -> list[dict]:
        cons = [{"type": "eq", "fun": lambda w: w.sum() - 1.0, "jac": lambda w: np.ones_like(w)}]
        for row, lo, hi in zip(self.g_mat, self.g_lo, self.g_hi):
            cons.append({"type": "ineq", "fun": lambda w, r=row, lo=lo: r @ w - lo, "jac": lambda w, r=row: r})
            cons.append({"type": "ineq", "fun": lambda w, r=row, hi=hi: hi - r @ w, "jac": lambda w, r=row: -r})
        return cons

    def _lp_bounds(self):
        return list(zip(self.lo, self.hi))

    def _lp(self, c: np.ndarray):
        """Optimise a linear objective over the feasible set (used for checks and extremes)."""
        a_ub = np.vstack([self.g_mat, -self.g_mat]) if len(self.g_mat) else None
        b_ub = np.concatenate([self.g_hi, -self.g_lo]) if len(self.g_mat) else None
        return linprog(c, A_ub=a_ub, b_ub=b_ub, A_eq=np.ones((1, self.n)), b_eq=[1.0],
                       bounds=self._lp_bounds(), method="highs")

    def _check_feasible(self) -> None:
        if np.any(self.lo > self.hi + _TOL):
            raise InfeasibleError("A minimum weight is above its maximum weight.")
        if self.lo.sum() > 1 + _TOL:
            raise InfeasibleError(f"Minimum weights add up to {self.lo.sum():.0%}, more than 100%.")
        if self.hi.sum() < 1 - _TOL:
            raise InfeasibleError(f"Maximum weights add up to {self.hi.sum():.0%}; they must allow 100%.")
        if not self._lp(np.zeros(self.n)).success:
            raise InfeasibleError("The group limits cannot all be satisfied at the same time.")

    def _start(self) -> np.ndarray:
        """A feasible starting point (the LP centre is not needed: any vertex works for SLSQP)."""
        res = self._lp(np.zeros(self.n))
        w = res.x if res.success else np.ones(self.n) / self.n
        return 0.5 * w + 0.5 * self._project_equal()

    def _project_equal(self) -> np.ndarray:
        w = np.clip(np.ones(self.n) / self.n, self.lo, self.hi)
        return w / w.sum()

    def _solve(self, fun, jac, extra=(), x0=None) -> np.ndarray:
        x0 = self._start() if x0 is None else x0
        res = minimize(fun, x0, jac=jac, method="SLSQP", bounds=self._lp_bounds(),
                       constraints=self._linear_constraints() + list(extra),
                       options={"ftol": 1e-12, "maxiter": 2000})
        if not res.success:
            raise RuntimeError(f"Optimiser did not converge: {res.message}")
        return self._clean(res.x)

    def _var(self, w):
        return float(w @ self.cov @ w)

    def _var_grad(self, w):
        return 2.0 * self.cov @ w

    # ------------------------------------------------------------------ mean-variance
    def min_variance(self) -> Portfolio:
        return self.evaluate(self._solve(self._var, self._var_grad), "Minimum variance")

    def max_return_portfolio(self) -> Portfolio:
        res = self._lp(-self.mu)
        return self.evaluate(self._clean(res.x), "Maximum return")

    def efficient_return(self, target: float, x0=None) -> Portfolio:
        """Least-variance portfolio with expected return exactly ``target``."""
        cons = [{"type": "eq", "fun": lambda w: w @ self.mu - target, "jac": lambda w: self.mu}]
        return self.evaluate(self._solve(self._var, self._var_grad, cons, x0), f"Target return {target:.1%}")

    def efficient_risk(self, target_vol: float) -> Portfolio:
        """Highest expected return with volatility at most ``target_vol``."""
        gmv = self.min_variance()
        if target_vol < gmv.volatility - 1e-6:
            raise InfeasibleError(f"No portfolio has volatility below {gmv.volatility:.2%} with these constraints.")
        top = self.max_return_portfolio()
        if target_vol >= top.volatility:
            top.name = f"Target volatility {target_vol:.1%}"
            return top
        cons = [{"type": "ineq", "fun": lambda w: target_vol ** 2 - self._var(w), "jac": lambda w: -self._var_grad(w)}]
        w = self._solve(lambda w: -float(w @ self.mu), lambda w: -self.mu, cons, x0=gmv.weights.values)
        return self.evaluate(w, f"Target volatility {target_vol:.1%}")

    def max_utility(self, risk_aversion: float = 3.0) -> Portfolio:
        """Maximise mu'w - (lambda / 2) w' Sigma w (mean-variance utility)."""
        lam = float(risk_aversion)
        w = self._solve(lambda w: -(w @ self.mu) + 0.5 * lam * self._var(w),
                        lambda w: -self.mu + lam * self.cov @ w)
        return self.evaluate(w, f"Max utility (lambda={lam:g})")

    def _max_ratio(self, a: np.ndarray) -> np.ndarray:
        """Maximise a'w / sqrt(w' Sigma w) over the feasible set.

        This ratio is not concave, but it is homogeneous of degree zero, so the
        Charnes-Cooper / Cornuejols-Tutuncu change of variables y = kappa w
        turns it into a convex QP:

            min y' Sigma y   s.t.  a'y = 1,  lo*kappa <= y <= hi*kappa,
                                  group_lo*kappa <= G y <= group_hi*kappa,
                                  kappa = sum(y) >= 0

        and w = y / sum(y). The global optimum is therefore guaranteed.
        """
        best = self._lp(-a)
        if not best.success or -best.fun <= 0:
            raise InfeasibleError("No feasible portfolio has a positive excess return.")
        n = self.n
        ones = np.ones(n)
        cons = [{"type": "eq", "fun": lambda y: a @ y - 1.0, "jac": lambda y: a}]
        for i in range(n):
            e = np.zeros(n)
            e[i] = 1.0
            cons.append({"type": "ineq", "fun": lambda y, e=e, i=i: e @ y - self.lo[i] * y.sum(),
                         "jac": lambda y, e=e, i=i: e - self.lo[i] * ones})
            cons.append({"type": "ineq", "fun": lambda y, e=e, i=i: self.hi[i] * y.sum() - e @ y,
                         "jac": lambda y, e=e, i=i: self.hi[i] * ones - e})
        for row, lo, hi in zip(self.g_mat, self.g_lo, self.g_hi):
            cons.append({"type": "ineq", "fun": lambda y, r=row, lo=lo: r @ y - lo * y.sum(),
                         "jac": lambda y, r=row, lo=lo: r - lo * ones})
            cons.append({"type": "ineq", "fun": lambda y, r=row, hi=hi: hi * y.sum() - r @ y,
                         "jac": lambda y, r=row, hi=hi: hi * ones - r})
        w0 = best.x
        y0 = w0 / (a @ w0)
        res = minimize(self._var, y0, jac=self._var_grad, method="SLSQP",
                       bounds=[(0.0, None)] * n, constraints=cons,
                       options={"ftol": 1e-14, "maxiter": 3000})
        if not res.success:
            raise RuntimeError(f"Optimiser did not converge: {res.message}")
        return self._clean(res.x / res.x.sum())

    def max_sharpe(self) -> Portfolio:
        """Tangency portfolio: highest (return - rf) / volatility."""
        return self.evaluate(self._max_ratio(self.mu - self.rf), "Maximum Sharpe")

    def max_diversification(self) -> Portfolio:
        """Choueifaty & Coignard (2008): maximise weighted average vol / portfolio vol."""
        sigma = np.sqrt(np.diag(self.cov))
        return self.evaluate(self._max_ratio(sigma), "Maximum diversification")

    def efficient_frontier(self, n_points: int = 60) -> list[Portfolio]:
        """Upper branch of the frontier, from the GMV to the maximum-return portfolio."""
        gmv = self.min_variance()
        top = self.max_return_portfolio()
        if top.expected_return - gmv.expected_return < 1e-6:
            return [gmv]
        targets = np.linspace(gmv.expected_return, top.expected_return, n_points)
        out, x0 = [gmv], gmv.weights.values
        for t in targets[1:-1]:
            try:
                p = self.efficient_return(float(t), x0=x0)
            except RuntimeError:
                continue
            out.append(p)
            x0 = p.weights.values
        out.append(top)
        return out

    # ------------------------------------------------------------------ heuristics
    def equal_weight(self) -> Portfolio:
        return self.evaluate(np.ones(self.n) / self.n, "Equal weight")

    def inverse_volatility(self) -> Portfolio:
        iv = 1.0 / np.sqrt(np.diag(self.cov))
        return self.evaluate(iv / iv.sum(), "Inverse volatility")

    def risk_parity(self, budgets=None) -> Portfolio:
        """Equal (or budgeted) risk contribution, via the convex program of Spinu (2013):

            min 0.5 y' Sigma y - sum_i b_i log(y_i),   y > 0,   w = y / sum(y)

        Its first-order condition is y_i (Sigma y)_i = b_i, i.e. each asset's
        risk contribution is proportional to its budget.
        """
        b = np.ones(self.n) / self.n if budgets is None else np.asarray(budgets, float) / np.sum(budgets)
        x0 = 1.0 / np.sqrt(np.diag(self.cov))
        res = minimize(lambda y: 0.5 * y @ self.cov @ y - b @ np.log(y), x0,
                       jac=lambda y: self.cov @ y - b / y, method="L-BFGS-B",
                       bounds=[(1e-12, None)] * self.n, options={"ftol": 1e-15, "gtol": 1e-12, "maxiter": 5000})
        w = res.x / res.x.sum()
        return self.evaluate(w, "Risk parity")

    def hierarchical_risk_parity(self) -> Portfolio:
        """Lopez de Prado (2016) HRP: cluster, quasi-diagonalise, recursive bisection.

        It never inverts the covariance matrix, so it is robust when assets are
        highly correlated (e.g. three different MSCI World trackers).
        """
        std = np.sqrt(np.diag(self.cov))
        corr = np.clip(self.cov / np.outer(std, std), -1.0, 1.0)
        dist = np.sqrt(np.clip(0.5 * (1.0 - corr), 0.0, None))
        np.fill_diagonal(dist, 0.0)
        if self.n == 1:
            return self.evaluate(np.ones(1), "HRP")
        order = leaves_list(linkage(squareform(dist, checks=False), method="single"))
        w = np.ones(self.n)
        clusters = [list(order)]
        while clusters:
            nxt = []
            for c in clusters:
                if len(c) <= 1:
                    continue
                half = len(c) // 2
                left, right = c[:half], c[half:]
                v_l, v_r = self._cluster_var(left), self._cluster_var(right)
                alpha = 1.0 - v_l / (v_l + v_r)
                w[left] *= alpha
                w[right] *= 1.0 - alpha
                nxt += [left, right]
            clusters = nxt
        return self.evaluate(w / w.sum(), "HRP")

    def _cluster_var(self, idx) -> float:
        sub = self.cov[np.ix_(idx, idx)]
        ivp = 1.0 / np.diag(sub)
        ivp /= ivp.sum()
        return float(ivp @ sub @ ivp)

    # ------------------------------------------------------------------ all at once
    def by_name(self, name: str) -> Portfolio:
        methods = {
            "Maximum Sharpe": self.max_sharpe,
            "Minimum variance": self.min_variance,
            "Maximum diversification": self.max_diversification,
            "Risk parity": self.risk_parity,
            "HRP": self.hierarchical_risk_parity,
            "Inverse volatility": self.inverse_volatility,
            "Equal weight": self.equal_weight,
        }
        if name not in methods:
            raise KeyError(f"Unknown strategy {name!r}; choose from {list(methods)}")
        return methods[name]()

    def standard_portfolios(self) -> dict[str, Portfolio]:
        """Every strategy the app compares, skipping any that is infeasible."""
        out: dict[str, Portfolio] = {}
        for name in STRATEGIES:
            try:
                out[name] = self.by_name(name)
            except (InfeasibleError, RuntimeError):
                continue
        return out


# --------------------------------------------------------------------------- analytics
def risk_contributions(weights: pd.Series, cov: pd.DataFrame) -> pd.Series:
    """Share of portfolio variance coming from each asset (sums to 1).

    RC_i = w_i (Sigma w)_i / (w' Sigma w). A 60/40 portfolio typically has
    ~90% of its risk in the equity sleeve: weights and risk are not the same.
    """
    w = weights.reindex(cov.index).fillna(0.0).values
    marginal = cov.values @ w
    total = float(w @ marginal)
    return pd.Series(w * marginal / total if total > 0 else np.zeros_like(w), index=cov.index)


def diversification_ratio(weights: pd.Series, cov: pd.DataFrame) -> float:
    w = weights.reindex(cov.index).fillna(0.0).values
    sigma = np.sqrt(np.diag(cov.values))
    vol = np.sqrt(w @ cov.values @ w)
    return float(w @ sigma / vol) if vol > 0 else 1.0


def effective_n(weights: pd.Series) -> float:
    """Inverse Herfindahl index: how many equally weighted assets this is 'worth'."""
    w = weights.values
    s = float((w ** 2).sum())
    return 1.0 / s if s > 0 else 0.0


def random_portfolios(mu: pd.Series, cov: pd.DataFrame, n: int = 3000, seed: int = 7) -> pd.DataFrame:
    """Random long-only portfolios (flat Dirichlet) for the cloud behind the frontier."""
    rng = np.random.default_rng(seed)
    w = rng.dirichlet(np.full(len(mu), 0.6), size=n)
    ret = w @ mu.values
    vol = np.sqrt(np.einsum("ij,jk,ik->i", w, cov.values, w))
    return pd.DataFrame({"Return": ret, "Volatility": vol})
