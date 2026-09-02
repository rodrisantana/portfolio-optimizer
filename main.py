import os
import matplotlib.pyplot as plt
from data.fetcher import DataFetcher
from optimizer.markowitz import MarkowitzOptimizer
from visualization.plotter import Plotter

# --- Configuration ---
TICKERS = ["AAPL", "MSFT", "JPM", "JNJ", "XOM", "AMZN", "GOOGL", "BRK-B"]
START_DATE = "2019-01-01"
END_DATE = "2026-01-01"

# Average 3M US T-bill over 2019-2025 (~2.5%), NOT today's rate.
# The tangency portfolio's composition depends on this input.
RISK_FREE_RATE = 0.025
OUTPUT_DIR = "outputs"


def save_results(min_var: dict, max_sharpe: dict, tickers: list, output_dir: str) -> None:
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, "results.txt")

    with open(filepath, "w", encoding="utf-8") as file:
        file.write("MARKOWITZ PORTFOLIO OPTIMIZATION — RESULTS\n")
        file.write("=" * 50 + "\n\n")

        file.write("MINIMUM VARIANCE PORTFOLIO\n")
        file.write(f"  Return:     {min_var['return']:.2%}\n")
        file.write(f"  Volatility: {min_var['volatility']:.2%}\n")
        file.write(f"  Sharpe:     {min_var['sharpe']:.2f}\n")
        file.write("  Weights:\n")
        for ticker, weight in min_var["weights"].items():
            file.write(f"    {ticker:<8} {weight:.2%}\n")

        file.write("\n")

        file.write("MAXIMUM SHARPE PORTFOLIO\n")
        file.write(f"  Return:     {max_sharpe['return']:.2%}\n")
        file.write(f"  Volatility: {max_sharpe['volatility']:.2%}\n")
        file.write(f"  Sharpe:     {max_sharpe['sharpe']:.2f}\n")
        file.write("  Weights:\n")
        for ticker, weight in max_sharpe["weights"].items():
            file.write(f"    {ticker:<8} {weight:.2%}\n")

    print(f"Results saved to {filepath}")


def main():
    # --- Step 1: Fetch data ---
    print("Downloading price data...")
    fetcher = DataFetcher(tickers=TICKERS, start=START_DATE, end=END_DATE)
    fetcher.fetch()
    returns = fetcher.get_returns()
    print(f"Data ready: {returns.shape[0]} trading days, {returns.shape[1]} assets\n")

    # --- Step 2: Optimize ---
    print("Running Markowitz optimization...")
    optimizer = MarkowitzOptimizer(returns=returns, risk_free_rate=RISK_FREE_RATE)
    frontier = optimizer.efficient_frontier()
    min_var = optimizer.min_variance_portfolio()
    max_sharpe = optimizer.max_sharpe_portfolio()

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
    save_results(min_var, max_sharpe, TICKERS, OUTPUT_DIR)

    # --- Step 5: Generate and save charts ---
    print("\nGenerating charts...")
    plotter = Plotter(tickers=TICKERS, output_dir=OUTPUT_DIR)
    plotter.plot_efficient_frontier(frontier, min_var, max_sharpe)
    plotter.plot_weights(min_var, title="Minimum Variance Portfolio")
    plotter.plot_weights(max_sharpe, title="Maximum Sharpe Portfolio")

    # Show all figures at once — no need to close each one manually
    plt.show()


if __name__ == "__main__":
    main()