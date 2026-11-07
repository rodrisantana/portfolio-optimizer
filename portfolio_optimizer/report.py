"""End-to-end run from a TOML config, producing a self-contained HTML report."""

from __future__ import annotations

import html
import tomllib
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from . import charts, estimators
from . import metrics as M
from .backtest import lookback_start, run_backtest, static_weights, walk_forward
from .catalog import describe
from .data import PERIODS_PER_YEAR, PriceData, load_demo, load_prices, to_returns
from .montecarlo import SimulationInput, simulate
from .optimizer import Constraints, GroupLimit, Portfolio, PortfolioOptimizer, risk_contributions


@dataclass
class RunResult:
    data: PriceData
    mu: pd.Series
    cov: pd.DataFrame
    portfolios: dict[str, Portfolio]
    frontier: list[Portfolio]
    backtest: pd.DataFrame | None
    backtest_stats: pd.DataFrame | None
    simulation: object | None
    config: dict


def load_config(path: str | Path) -> dict:
    with open(path, "rb") as fh:
        return tomllib.load(fh)


def run(config: dict) -> RunResult:
    u, e, c = config["universe"], config.get("estimation", {}), config.get("constraints", {})
    if u.get("offline_demo"):
        demo = load_demo()
        cols = [a for a in u.get("assets", []) if a in demo.prices.columns] or list(demo.prices.columns)
        data = PriceData(demo.prices[cols], "EUR", {x: "EUR" for x in cols}, {x: x for x in cols})
    else:
        data = load_prices(u["assets"], u.get("base_currency", "EUR"), u.get("start"), u.get("end"),
                           backfill=u.get("backfill_funds", True))
    prices = data.prices.rename(columns={x: describe(x).display for x in data.prices.columns})
    freq = e.get("frequency", "weekly")
    ppy = PERIODS_PER_YEAR[freq]
    rets = to_returns(prices, freq)
    mu = estimators.expected_returns(rets, ppy, e.get("expected_returns", "bayes_stein"))
    cov = estimators.nearest_psd(estimators.covariance(rets, ppy, e.get("covariance", "ledoit_wolf")))
    rf = float(e.get("risk_free_rate", 0.02))
    label = {x: describe(x).display for x in data.prices.columns}
    groups = [GroupLimit(g["name"], [label.get(m, m) for m in g["members"]], g.get("lower", 0.0), g.get("upper", 1.0))
              for g in c.get("groups", [])]
    cons = Constraints(lower={a: c.get("min_weight", 0.0) for a in prices.columns},
                       default_upper=max(c.get("max_weight", 1.0), 1 / prices.shape[1]), groups=groups)
    opt = PortfolioOptimizer(mu, cov, rf, cons)
    portfolios = opt.standard_portfolios()
    frontier = opt.efficient_frontier(60)

    bt_wealth = bt_stats = None
    b = config.get("backtest")
    if b:
        lb = float(b.get("lookback_years", 3))
        start = lookback_start(prices, lb)
        if start < prices.index[-1] - pd.Timedelta(days=365):
            curves = {}
            for name in b.get("strategies", ["Maximum Sharpe", "Equal weight"]):
                fn = (static_weights(portfolios[name].weights) if name == "Equal weight" else
                      walk_forward(name, lb, freq, e.get("expected_returns", "bayes_stein"),
                                   e.get("covariance", "ledoit_wolf"), rf, cons))
                curves[name] = run_backtest(prices, fn, name, b.get("rebalance", "Quarterly"), start,
                                            float(b.get("cost_bps", 10))).wealth
            bt_wealth = pd.DataFrame(curves)
            bt_stats = M.summary_table(bt_wealth.pct_change().dropna(), 252, rf)

    sim = None
    m = config.get("montecarlo")
    if m:
        p = portfolios[m.get("portfolio", "Maximum Sharpe")]
        ter = pd.Series({label[x]: describe(x).ter for x in data.prices.columns})
        inp = SimulationInput(initial=m.get("initial", 10_000), monthly_contribution=m.get("monthly_contribution", 0),
                              years=int(m.get("years", 20)), expected_return=m.get("expected_return", p.expected_return),
                              volatility=m.get("volatility", p.volatility), annual_fee=float(p.weights @ ter),
                              inflation=m.get("inflation", 0.02), method=m.get("method", "lognormal"),
                              n_sims=int(m.get("simulations", 5000)), target=m.get("goal"))
        hist = to_returns(prices, "monthly") @ p.weights.values
        sim = simulate(inp, history=hist)

    return RunResult(data, mu, cov, portfolios, frontier, bt_wealth, bt_stats, sim, config)


def _table(df: pd.DataFrame, pct_cols=(), dec_cols=()) -> str:
    fmt = df.copy().astype(object)
    for col in df.columns:
        if col in pct_cols:
            fmt[col] = df[col].map(lambda v: f"{v:.2%}")
        elif col in dec_cols:
            fmt[col] = df[col].map(lambda v: f"{v:.2f}")
    return fmt.to_html(classes="tbl", border=0, escape=True)


def results_markdown(res: RunResult) -> str:
    lines = ["| Portfolio | Return | Volatility | Sharpe |", "|---|---|---|---|"]
    for name, p in res.portfolios.items():
        lines.append(f"| {name} | {p.expected_return:.2%} | {p.volatility:.2%} | {p.sharpe:.2f} |")
    return "\n".join(lines) + "\n"


def write_report(res: RunResult, out_dir: str | Path) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    prices = res.data.prices.rename(columns={x: describe(x).display for x in res.data.prices.columns})
    colors = charts.color_map(list(prices.columns))
    rf = float(res.config.get("estimation", {}).get("risk_free_rate", 0.02))
    asset_vol = pd.Series((res.cov.values.diagonal()) ** 0.5, index=res.cov.index)

    figs = [("Efficient frontier", charts.efficient_frontier(res.frontier, res.portfolios, res.mu, asset_vol, rf,
                                                             asset_colors=colors)),
            ("Weights", charts.weights_bars(pd.DataFrame({n: p.weights for n, p in res.portfolios.items()}))),
            ("Risk contribution of the maximum Sharpe portfolio",
             charts.risk_vs_weight(res.portfolios["Maximum Sharpe"].weights,
                                   risk_contributions(res.portfolios["Maximum Sharpe"].weights, res.cov))),
            ("Growth of 100", charts.growth_chart(prices / prices.iloc[0] * 100, colors, True)),
            ("Correlation", charts.correlation_heatmap(estimators.cov_to_corr(res.cov)))]
    if res.backtest is not None:
        bcol = charts.color_map(list(res.backtest.columns))
        figs.append(("Walk-forward backtest (out-of-sample)", charts.growth_chart(res.backtest * 100, bcol)))
        figs.append(("Backtest drawdowns", charts.drawdown_chart(res.backtest, bcol)))
    if res.simulation is not None:
        sim = res.simulation
        figs.append(("Monte Carlo projection (today's money)",
                     charts.fan_chart(sim.percentiles(real=True), sim.contributed / sim.deflator, sim.inputs.target)))

    port_table = pd.DataFrame([p.as_row() for p in res.portfolios.values()]).set_index("Portfolio")
    weights = pd.DataFrame({n: p.weights for n, p in res.portfolios.items()})
    sections = [f"<h2>Portfolios</h2>{_table(port_table, ('Return', 'Volatility'), ('Sharpe',))}",
                f"<h2>Weights</h2>{_table(weights, tuple(weights.columns))}"]
    if res.backtest_stats is not None:
        bt = res.backtest_stats[["CAGR", "Volatility", "Sharpe", "Max drawdown", "CVaR 95%"]]
        bt_html = _table(bt, ("CAGR", "Volatility", "Max drawdown", "CVaR 95%"), ("Sharpe",))
        sections.append(f"<h2>Backtest statistics</h2>{bt_html}")
    if res.simulation is not None:
        s = res.simulation.summary()
        rows = "".join(f"<tr><td>{html.escape(k)}</td><td>{v:,.2f}</td></tr>" if abs(v) > 1 else
                       f"<tr><td>{html.escape(k)}</td><td>{v:.1%}</td></tr>" for k, v in s.items())
        sections.append(f"<h2>Monte Carlo summary</h2><table class='tbl'>{rows}</table>")
    for i, (title, fig) in enumerate(figs):
        sections.append(f"<h2>{html.escape(title)}</h2>" +
                        fig.to_html(full_html=False, include_plotlyjs="cdn" if i == 0 else False))

    period = f"{prices.index[0]:%d %b %Y} to {prices.index[-1]:%d %b %Y}"
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Portfolio report</title>
<style>
body{{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;max-width:1100px;margin:0 auto;padding:24px 16px;
color:#0b0b0b;background:#fcfcfb}} h1{{margin-bottom:4px}} .muted{{color:#52514e}}
.tbl{{border-collapse:collapse;font-size:14px;font-variant-numeric:tabular-nums;margin:8px 0 24px}}
.tbl td,.tbl th{{padding:6px 10px;border-bottom:1px solid #e1e0d9;text-align:right}}
.tbl th:first-child,.tbl td:first-child{{text-align:left}}
@media (prefers-color-scheme: dark){{body{{background:#1a1a19;color:#f0efec}} .muted{{color:#c3c2b7}}
.tbl td,.tbl th{{border-color:#2c2c2a}}}}
</style></head><body>
<h1>Portfolio report</h1>
<p class="muted">{len(prices.columns)} assets in {res.data.base_currency}, {period}. Generated with portfolio-optimizer.
In-sample statistics overstate what an optimised portfolio will deliver; see the out-of-sample backtest.</p>
{''.join(sections)}
</body></html>"""
    path = out / "report.html"
    path.write_text(doc, encoding="utf-8")
    (out / "results.md").write_text(results_markdown(res), encoding="utf-8")
    return path
