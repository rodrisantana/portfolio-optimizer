import numpy as np # NumPy for numerical operations and array handling.
from scipy.optimize import minimize  # SciPy's optimization library for solving constrained optimization problems.


class MarkowitzOptimizer:
    """
    Computes the efficient frontier, minimum variance portfolio,
    and maximum Sharpe ratio portfolio using Markowitz mean-variance theory.
    """

    def __init__(self, returns, risk_free_rate: float = 0.02):
        self.returns = returns # Store daily returns DataFrame for reference
        
        self.mu = returns.mean().values # mu: expected daily return for each asset (vector of means)

        self.covariance = returns.cov().values # cov: covariance matrix between all asset pairs (n x n matrix)

        self.num_assets = len(self.mu) # number of assets in the portfolio

        self.risk_free_rate = risk_free_rate / 252 # convert annual risk-free rate to daily (252 trading days per year)

    def portfolio_performance(self, weights: np.ndarray) -> tuple:
        # Annualized return: return_p = weights^T * mu * 252
        ret = np.dot(weights, self.mu) * 252

        # Annualized volatility: sigma_p = sqrt(weights^T * Sigma * weights * 252)
        volatility = np.sqrt(np.dot(weights, np.dot(self.covariance, weights)) * 252)

        # Sharpe ratio: excess return per unit of risk
        sharpe = (ret - self.risk_free_rate * 252) / volatility

        return ret, volatility, sharpe

    def _min_variance_for_target(self, target_return: float) -> np.ndarray:
        # Constraint 1: weights must sum to 1 (fully invested portfolio)
        # Constraint 2: portfolio return must equal the target return
        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1},
            {"type": "eq", "fun": lambda w: np.dot(w, self.mu) * 252 - target_return},
        ]

        # Bounds: no short selling, each weight between 0 and 1
        bounds = [(0, 1)] * self.num_assets

        # Initial guess: equal weight portfolio
        w0 = np.ones(self.num_assets) / self.num_assets

        # Minimize portfolio variance w^T * Sigma * w subject to constraints
        # SLSQP = Sequential Least Squares Programming, handles equality constraints
        result = minimize(
            lambda w: np.dot(w, np.dot(self.covariance, w)),
            w0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )

        # Return optimal weights if solver converged, else None
        return result.x if result.success else None

    def efficient_frontier(self, n_points: int = 100) -> list:
        # Sweep target returns from the lowest to highest individual asset return
        min_ret = self.mu.min() * 252
        max_ret = self.mu.max() * 252
        targets = np.linspace(min_ret, max_ret, n_points)

        frontier = []
        for target in targets:
            # For each target return, find the minimum variance portfolio
            w = self._min_variance_for_target(target)
            if w is not None:
                ret, vol, sharpe = self.portfolio_performance(w)
                frontier.append((ret, vol, sharpe, w))

        # Each point in frontier is (return, volatility, sharpe, weights)
        return frontier

    def min_variance_portfolio(self) -> dict:
        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
        bounds = [(0, 1)] * self.num_assets
        best_result = None

        # Run optimizer from multiple random starting points to avoid local minima
        for _ in range(20):
            w0 = np.random.dirichlet(np.ones(self.num_assets))
            result = minimize(
                lambda w: np.dot(w, np.dot(self.covariance, w)),
                w0,
                method="SLSQP",
                bounds=bounds,
                constraints=constraints,
            )
            if result.success:
                if best_result is None or result.fun < best_result.fun:
                    best_result = result

        w = best_result.x
        ret, vol, sharpe = self.portfolio_performance(w)
        return {"weights": w, "return": ret, "volatility": vol, "sharpe": sharpe}

    def max_sharpe_portfolio(self) -> dict:
        # Maximize Sharpe ratio = minimize negative Sharpe ratio
        # This is the tangency portfolio: optimal combination of risky assets
        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
        bounds = [(0, 1)] * self.num_assets
        w0 = np.ones(self.num_assets) / self.num_assets

        result = minimize(
            lambda w: -self.portfolio_performance(w)[2],  # negative Sharpe
            w0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )

        w = result.x
        ret, vol, sharpe = self.portfolio_performance(w)
        return {"weights": w, "return": ret, "volatility": vol, "sharpe": sharpe}