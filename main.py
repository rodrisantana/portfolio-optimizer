import os
from pathlib import Path
import matplotlib.pyplot as plt
from data.fetcher import DataFetcher
from optimizer.markowitz import MarkowitzOptimizer
from visualization.plotter import Plotter

# Resolve paths relative to this file, not to the current working directory,
# so the script produces identical output regardless of where it is launched from.
PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "outputs"
CACHE_PATH = PROJECT_ROOT / "data" / "prices.csv"

# --- Configuration ---
TICKERS = ["AAPL", "MSFT", "JPM", "JNJ", "XOM", "AMZN", "GOOGL", "BRK-B"]
START_DATE = "2019-01-01"
END_DATE = "2026-01-01"

# Average 3M US T-bill over 2019-2025 (~2.5%), NOT today's rate.
# The tangency portfolio's composition depends on this input.
RISK_FREE_RATE = 0.025
OUTPUT_DIR = "outputs"


def save_results(min_var: dict, max_sharpe: dict, output_dir: str) -> None:
    os.makedirs(output_dir, exist_ok=True)

    with open(os.path.join(output_dir, "results.txt"), "w", encoding="utf-8") as file:
        file.write("MARKOWITZ PORTFOLIO OPTIMIZATION - RESULTS\n")
        file.write("=" * 50 + "\n\n")
        for name, p in [("MINIMUM VARIANCE PORTFOLIO", min_var),
                        ("MAXIMUM SHARPE PORTFOLIO", max_sharpe)]:
            file.write(f"{name}\n")
            file.write(f"  Return:     {p['return']:.2%}\n")
            file.write(f"  Volatility: {p['volatility']:.2%}\n")
            file.write(f"  Sharpe:     {p['sharpe']:.2f}\n")
            file.write("  Weights:\n")
            for ticker, weight in p["weights"].items():
                file.write(f"    {ticker:<8} {weight:.2%}\n")
            file.write("\n")

    # Markdown table so the README can never drift from the actual run
    with open(os.path.join(output_dir, "results.md"), "w", encoding="utf-8") as file:
        file.write("| Portfolio | Return | Volatility | Sharpe |\n")
        file.write("|---|---|---|---|\n")
        for name, p in [("Minimum Variance", min_var), ("Maximum Sharpe", max_sharpe)]:
            file.write(f"| {name} | {p['return']:.2%} | {p['volatility']:.2%} "
                    f"| {p['sharpe']:.2f} |\n")

    print(f"Results saved to {output_dir}/")


def main():
    # --- Step 1: Fetch data ---
    print("Downloading price data...")
    fetcher = DataFetcher(tickers=TICKERS, start=START_DATE, end=END_DATE)
    fetcher.fetch(cache_path=CACHE_PATH)
    returns = fetcher.get_returns()
    print(f"Data ready: {returns.shape[0]} trading days, {returns.shape[1]} assets\n")

    # --- Step 2: Optimize ---
    print("Running Markowitz optimization...")
    optimizer = MarkowitzOptimizer(returns=returns, risk_free_rate=RISK_FREE_RATE)
    frontier = optimizer.efficient_frontier()
    min_var = optimizer.min_variance_portfolio()
    max_sharpe = optimizer.max_sharpe_portfolio()

    # Sanity checks: these must hold by construction if the optimiser is correct.
    # The GMV is the leftmost point of the frontier, and no frontier portfolio
    # can have a higher Sharpe than the tangency portfolio.
    assert min_var["volatility"] <= min(p["volatility"] for p in frontier) + 1e-9
    assert max_sharpe["sharpe"] >= max(p["sharpe"] for p in frontier) - 1e-9

    # --- Step 3: Print results ---
    print("Minimum Variance Portfolio:")
    print(f"  Return:     {min_var['return']:.2%}")
    print(f"  Volatility: {min_var['volatility']:.2%}")
    print(f"  Sharpe:     {min_var['sharpe']:.2f}")
    for ticker, weight in min_var["weights"].items():
        print(f"    {ticker:<8} {weight:.2%}")

    print("\nMaximum Sharpe Portfolio:")
    print(f"  Return:     {max_sharpe['return']:.2%}")
    print(f"  Volatility: {max_sharpe['volatility']:.2%}")
    print(f"  Sharpe:     {max_sharpe['sharpe']:.2f}")
    for ticker, weight in max_sharpe["weights"].items():
        print(f"    {ticker:<8} {weight:.2%}")

    # --- Step 4: Save results to txt ---
    save_results(min_var, max_sharpe, OUTPUT_DIR)

    # --- Step 5: Generate and save charts ---
    print("\nGenerating charts...")
    plotter = Plotter(output_dir=OUTPUT_DIR)
    plotter.plot_efficient_frontier(frontier, min_var, max_sharpe)
    plotter.plot_weights(min_var, title="Minimum Variance Portfolio")
    plotter.plot_weights(max_sharpe, title="Maximum Sharpe Portfolio")

    # Show all figures at once — no need to close each one manually
    plt.show()


if __name__ == "__main__":
    main()