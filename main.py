"""Command-line entry point: optimise, backtest and project, then write an HTML report.

    python main.py                       # uses config.toml
    python main.py --config my.toml
    python main.py --demo                # offline, uses the bundled dataset
"""

from __future__ import annotations

import argparse
from pathlib import Path

from portfolio_optimizer.report import load_config, run, write_report

ROOT = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default=ROOT / "config.toml", help="TOML configuration file")
    parser.add_argument("--out", default=ROOT / "outputs", help="output folder")
    parser.add_argument("--demo", action="store_true", help="use the offline demo dataset")
    args = parser.parse_args()

    config = load_config(args.config)
    if args.demo:
        from portfolio_optimizer.data import load_demo
        config["universe"]["offline_demo"] = True
        config["universe"]["assets"] = [c for c in load_demo().prices.columns if c != "XEON.DE"]
        config["constraints"].pop("groups", None)

    print("Loading prices and optimising...")
    res = run(config)
    prices = res.data.prices
    print(f"{prices.shape[1]} assets, {prices.index[0]:%Y-%m-%d} to {prices.index[-1]:%Y-%m-%d}, "
          f"base currency {res.data.base_currency}")
    for w in res.data.warnings:
        print("  note:", w)

    print(f"\n{'Portfolio':<26}{'Return':>9}{'Vol':>9}{'Sharpe':>8}")
    for name, p in res.portfolios.items():
        print(f"{name:<26}{p.expected_return:>9.2%}{p.volatility:>9.2%}{p.sharpe:>8.2f}")

    best = res.portfolios["Maximum Sharpe"]
    print("\nMaximum Sharpe weights:")
    for asset, w in best.weights[best.weights > 1e-4].sort_values(ascending=False).items():
        print(f"  {asset:<26}{w:>7.1%}")

    if res.backtest_stats is not None:
        print("\nOut-of-sample backtest:")
        print(res.backtest_stats[["CAGR", "Volatility", "Sharpe", "Max drawdown"]].to_string(
            float_format=lambda v: f"{v:.3f}"))

    if res.simulation is not None:
        s = res.simulation.summary()
        median = s["Median final value (today's money)"]
        low = s["Pessimistic (P5, today's money)"]
        print(f"\nMonte Carlo ({res.simulation.inputs.years} years): median {median:,.0f} in today's money, "
              f"P5 {low:,.0f}")
        if "Probability of reaching the goal" in s:
            print(f"Probability of reaching the goal: {s['Probability of reaching the goal']:.0%}")

    path = write_report(res, args.out)
    print(f"\nReport written to {path}")


if __name__ == "__main__":
    main()
