import numpy as np
import pandas as pd
from scipy.optimize import minimize

TRADING_DAYS = 252


class MarkowitzOptimizer:
    """Mean-variance optimisation on annualised inputs."""

    def __init__(self, returns: pd.DataFrame, risk_free_rate: float = 0.025):
        # Asset labels are stored ONCE and travel with every weight vector.
        self.assets = list(returns.columns)
        self.num_assets = len(self.assets)

        # Annualise here, once. Everything downstream works in annual units.
        # .values works with NumPy arrays which are computationally much faster
        self.mu = returns.mean().values * TRADING_DAYS # Expected returns vector,  
        self.covariance = returns.cov().values * TRADING_DAYS # Covariance matrix

        # Risk-free rate stays ANNUAL. No conversion, no unit confusion.
        self.rf_rate = risk_free_rate

    # ---------- helpers ----------
    def _variance(self, weights: np.ndarray) -> float:
        # weight matrix (w) @ covariance matrix @ weight matrix (w) = portfolio variance
        # @ operator is matrix multiplication in NumPy. It is equivalent to np.dot(w, np.dot(self.covariance, w))
        return float(weights @ self.covariance @ weights) 

    def _pack(self, weights: np.ndarray) -> dict:
        # It takes the array returned by the solver and packages it into a labelled dictionary with all the relevant metrics.
        portfolio_exp_return = float(weights @ self.mu) # Weights (w) @ Expected returns (mu) = portfolio expected return
        portfolio_volatility = float(np.sqrt(weights @ self.covariance @ weights)) # Weights (w) @ Covariance (Sigma) @ Weights (w) = portfolio variance
        
        return {
            "weights": pd.Series(weights, index=self.assets),  # labelled, not a bare array
            "return": portfolio_exp_return,
            "volatility": portfolio_volatility,
            # Sharpe ratio is (portfolio return - risk-free rate) / portfolio volatility
            "sharpe": (portfolio_exp_return - self.rf_rate) / portfolio_volatility if portfolio_volatility != 0 else 0,
        }

    def _solve_qp(self, objective, constraints, bounds, w0):
        # SQLQP (Sequential Least Squares Quadratic Programming) is a gradient-based solver. 
        # It is fast and accurate, but it is not guaranteed to converge to a solution. 
        # The `ftol` parameter controls the tolerance for convergence. 
        # With annualised variance (~0.03) the default 1e-6 is borderline; 1e-12 forces to try harder to find a solution. 
        # The `maxiter` parameter controls the maximum number of iterations the solver will perform. 
        # If the solver does not converge within this limit, it will raise an error.     
        # 'w0' is the initial guess for the weights. It is important to provide a reasonable starting point for the solver to converge.   
        result = minimize(
            objective, w0, method="SLSQP",
            bounds=bounds, constraints=constraints,
            options={"ftol": 1e-12, "maxiter": 1000},
        )
        if not result.success:
            raise RuntimeError(f"SLSQP failed to converge: {result.message}")
        return result

    # ---------- portfolios ----------
    def min_variance_portfolio(self) -> dict:
        # Convex QP over a simplex: the local optimum IS the global optimum.
        # One deterministic start is sufficient. No random restarts needed.
        constraints = [{"type": "eq", "fun": lambda weights: weights.sum() - 1.0}] # The sum of the weights must equal 1 (fully invested portfolio)
        result = self._solve_qp(self._variance, constraints,
                             [(0.0, 1.0)] * self.num_assets, # Every weight must be between 0 and 1 (no short selling)
                             np.ones(self.num_assets) / self.num_assets) # Equiweighted starting point: 1/N for each asset, where N is the number of assets
        return self._pack(result.x) 

    def _min_var_for_target(self, target: float):
        constraints = [
            {"type": "eq", "fun": lambda weights: weights.sum() - 1.0},
            # New restriction: the portfolio expected return must equal the target return
            {"type": "eq", "fun": lambda weights, t=target: weights @ self.mu - t}, 
            # t = target is set locally to avoid closure bug with lambda functions in loops. 
        ]
        try:
            result = self._solve_qp(self._variance, constraints,
                                 [(0.0, 1.0)] * self.num_assets,
                                 np.ones(self.num_assets) / self.num_assets)
            return result.x
        except RuntimeError:
            return None

    def efficient_frontier(self, n_points: int = 100) -> list:
        # Start the sweep at the GMV (Global Minimum Variance) return, not at min(mu): everything below
        # the GMV is the dominated lower branch and is NOT efficient.
        gmv_return = self.min_variance_portfolio()["return"]
        
        #Uses np.linspace to generate n_points evenly spaced target returns between the GMV return and the maximum expected return of the assets.
        targets = np.linspace(gmv_return, self.mu.max(), n_points)

        frontier, failed = [], 0
        # Loop: for each return target, find the minimum variance portfolio that achieves that return. 
        # If the solver fails to converge, increment the failed counter and continue to the next target.
        for t in targets:
            weights= self._min_var_for_target(t)
            if weights is None:
                failed += 1
                continue
            frontier.append(self._pack(weights))

        if failed:
            print(f"WARNING: {failed}/{n_points} frontier targets failed to converge")
        return frontier

    def max_sharpe_portfolio(self) -> dict:
        # Maximising the Sharpe ratio directly is a NON-convex problem.
        # Cornuejols-Tutuncu transformation turns it into a convex QP:
        #   min y'Sy  s.t.  (mu - rf)'y = 1,  y >= 0
        # then rescale weights=  y / sum(y). Global optimum guaranteed.
        
        excess = self.mu - self.rf_rate # Calculate excess returns for each asset
        if excess.max() <= 0:
            raise ValueError("No asset has positive excess return; tangency undefined.")

        constraints = [{"type": "eq", "fun": lambda y: excess @ y - 1.0}] 
        # The numerator of the Sharpe ratio is set to 1, which is a standard transformation in the Cornuejols-Tutuncu method.
        
        result = self._solve_qp(self._variance, constraints,
                             [(0.0, None)] * self.num_assets, # Now there is no upper bound on the weights, but they must be >= 0 (no short selling).
                             np.ones(self.num_assets) / self.num_assets)

        weights= result.x / result.x.sum() # Rescale the weights to ensure they sum to 1, which is necessary for a valid portfolio allocation.
        return self._pack(weights)