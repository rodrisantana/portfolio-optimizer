import matplotlib.pyplot as plt
import numpy as np
import os


class Plotter:
    """
    Visualizes the efficient frontier and key portfolios.
    """

    def __init__(self, tickers: list[str], output_dir: str = "outputs"):
        self.tickers = tickers
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        self.output_dir = output_dir

    def plot_efficient_frontier(self, frontier: list, min_var: dict, max_sharpe: dict) -> None:
        returns = [p[0] for p in frontier]
        volatilities = [p[1] for p in frontier]
        sharpes = [p[2] for p in frontier]

        fig, ax = plt.subplots(figsize=(10, 6))

        sc = ax.scatter(
            volatilities, returns, c=sharpes,
            cmap="viridis", s=15, zorder=2, label="Efficient frontier",
        )
        plt.colorbar(sc, ax=ax, label="Sharpe Ratio")

        ax.scatter(
            min_var["volatility"], min_var["return"],
            marker="*", color="blue", s=200, zorder=3,
            label=f"Min Variance  (Sharpe {min_var['sharpe']:.2f})",
        )
        ax.scatter(
            max_sharpe["volatility"], max_sharpe["return"],
            marker="*", color="red", s=200, zorder=3,
            label=f"Max Sharpe  (Sharpe {max_sharpe['sharpe']:.2f})",
        )

        ax.set_xlabel("Annualized Volatility")
        ax.set_ylabel("Annualized Return")
        ax.set_title("Efficient Frontier — Markowitz Portfolio Optimization")
        ax.legend()
        ax.grid(True, linestyle="--", alpha=0.5)
        plt.tight_layout()

        # Save to outputs folder, do not call plt.show() here
        plt.savefig(os.path.join(self.output_dir, "efficient_frontier.png"), dpi=150)

    def plot_weights(self, portfolio: dict, title: str) -> None:
        weights = portfolio["weights"]
        fig, ax = plt.subplots(figsize=(8, 5))

        colors = plt.cm.viridis(np.linspace(0.2, 0.8, len(self.tickers)))
        ax.bar(self.tickers, weights, color=colors)

        ax.set_xlabel("Asset")
        ax.set_ylabel("Weight")
        ax.set_title(title)
        ax.grid(True, axis="y", linestyle="--", alpha=0.5)
        plt.tight_layout()

        # Save to outputs folder, do not call plt.show() here
        filename = title.replace(" ", "_") + ".png"
        plt.savefig(os.path.join(self.output_dir, filename), dpi=150)