"""Interactive portfolio lab: optimise, backtest and project a portfolio of ETFs, ETCs and index funds.

Run with:  streamlit run app.py
"""

from __future__ import annotations

import json
from datetime import date

import numpy as np
import pandas as pd
import streamlit as st

from portfolio_optimizer import charts, estimators
from portfolio_optimizer import metrics as M
from portfolio_optimizer.backtest import REBALANCE_RULES, lookback_start, run_backtest, static_weights, walk_forward
from portfolio_optimizer.catalog import ASSET_CLASSES, CATALOG, PRESETS, describe
from portfolio_optimizer.data import PERIODS_PER_YEAR, PriceData, load_demo, load_prices, parse_uploaded_csv, to_returns
from portfolio_optimizer.holdings import Holding, rebalance_plan, tracking_gap
from portfolio_optimizer.montecarlo import METHODS, SimulationInput, required_contribution, simulate
from portfolio_optimizer.optimizer import (
    CONSTRAINED,
    STRATEGIES,
    Constraints,
    GroupLimit,
    InfeasibleError,
    PortfolioOptimizer,
    diversification_ratio,
    effective_n,
    random_portfolios,
    risk_contributions,
)

st.set_page_config(page_title="Portfolio Lab", page_icon="📈", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
.block-container {padding-top: 2rem; max-width: 1400px;}
[data-testid="stMetricValue"] {font-size: 1.55rem;}
[data-testid="stMetric"] {background: rgba(137,135,129,0.07); border-radius: 10px; padding: 12px 14px;}
.small-note {color: #898781; font-size: 0.85rem;}
</style>
""", unsafe_allow_html=True)

RETURN_LABELS = {"bayes_stein": "Bayes-Stein shrinkage (recommended)", "historical": "Historical mean",
                 "ewma": "Exponentially weighted mean"}
COV_LABELS = {"ledoit_wolf": "Ledoit-Wolf shrinkage (recommended)", "sample": "Sample covariance",
              "ewma": "Exponentially weighted (RiskMetrics)"}
CURRENCY_SYMBOL = {"EUR": "€", "USD": "$", "GBP": "£", "CHF": "CHF "}


def pct(x: float, d: int = 1) -> str:
    return "n/a" if x is None or not np.isfinite(x) else f"{x:.{d}%}"


def money(x: float, ccy: str) -> str:
    sym = CURRENCY_SYMBOL.get(ccy, ccy + " ")
    return f"{sym}{x:,.0f}"


# =========================================================================== cached computations
@st.cache_data(show_spinner=False, ttl=6 * 3600)
def get_prices(ids: tuple[str, ...], base: str, backfill: bool, clean: bool, upload: bytes | None) -> PriceData:
    uploaded = parse_uploaded_csv(upload) if upload else None
    return load_prices(list(ids), base, backfill=backfill, clean_spikes=clean, uploaded=uploaded)


@st.cache_data(show_spinner=False)
def get_estimates(returns: pd.DataFrame, ppy: int, r_method: str, c_method: str):
    mu = estimators.expected_returns(returns, ppy, r_method)
    if c_method == "ledoit_wolf":
        cov, delta = estimators.ledoit_wolf_cov(returns, ppy)
    else:
        cov, delta = estimators.covariance(returns, ppy, c_method), None
    cov = estimators.nearest_psd(cov)
    phi = estimators.bayes_stein_mean(returns, ppy)[1] if r_method == "bayes_stein" else None
    se = estimators.mean_standard_error(returns, ppy)
    return mu, cov, {"delta": delta, "phi": phi, "se": se}


def _constraints_from_json(spec: str) -> Constraints:
    d = json.loads(spec)
    return Constraints(lower=d["lower"], upper=d["upper"], default_upper=d["default_upper"],
                       groups=[GroupLimit(**g) for g in d["groups"]])


@st.cache_data(show_spinner=False)
def get_portfolios(mu: pd.Series, cov: pd.DataFrame, rf: float, spec: str, n_points: int = 60):
    cons = _constraints_from_json(spec)
    opt = PortfolioOptimizer(mu, cov, rf, cons)
    return opt.standard_portfolios(), opt.efficient_frontier(n_points)


@st.cache_data(show_spinner=False)
def get_cloud(mu: pd.Series, cov: pd.DataFrame) -> pd.DataFrame:
    return random_portfolios(mu, cov, 2500)


@st.cache_data(show_spinner=False)
def get_backtest(prices: pd.DataFrame, kind: str, name: str, weights: pd.Series | None, rebalance: str,
                 start: pd.Timestamp, cost_bps: float, ter: pd.Series | None, lookback: float, freq: str,
                 r_method: str, c_method: str, rf: float, spec: str):
    if kind == "static":
        fn = static_weights(weights)
    else:
        fn = walk_forward(name, lookback, freq, r_method, c_method, rf, _constraints_from_json(spec))
    return run_backtest(prices, fn, name, rebalance, start=start, cost_bps=cost_bps, ter=ter)


# =========================================================================== sidebar
DEFAULTS = {
    "source": "Yahoo Finance (live)", "preset": "(custom)",
    "catalog_assets": PRESETS["Boglehead core (world + EM + bonds + gold)"], "extra": "", "base": "EUR",
    "start": date(2015, 1, 1), "end": date.today(), "backfill": True, "clean": True,
    "freq": "weekly", "r_method": "bayes_stein", "c_method": "ledoit_wolf", "rf": 2.0, "max_w": 0.5, "min_w": 0.0,
}


def sidebar():
    for k_, v_ in DEFAULTS.items():
        st.session_state.setdefault(k_, v_)
    sb = st.sidebar
    sb.title("Portfolio Lab")
    sb.caption("Mean-variance and risk-based optimisation, backtests and Monte Carlo for ETFs, ETCs and index funds.")

    session = sb.file_uploader("Load a saved session (.json)", type=["json"], key="session_file",
                               help="Restores your universe, holdings and settings.")
    if session is not None and st.session_state.get("_loaded") != session.file_id:
        cfg = json.loads(session.getvalue())
        for k, v in cfg.get("widgets", {}).items():
            st.session_state[k] = v
        st.session_state["holdings_seed"] = cfg.get("holdings", {})
        for stale in ("holdings", "inst", "mu_edit", "groups"):
            st.session_state.pop(stale, None)
        st.session_state["_loaded"] = session.file_id
        st.rerun()

    source = sb.radio("Data source", ["Yahoo Finance (live)", "Offline demo dataset"], key="source",
                      help="The demo dataset ships with the repo (8 UCITS products in EUR, 2018-2026) "
                           "and works without internet.")
    demo = source.startswith("Offline")

    if demo:
        demo_cols = list(load_demo().prices.columns)
        st.session_state.setdefault("demo_assets", [c for c in demo_cols if c != "XEON.DE"])
        chosen = sb.multiselect("Assets", demo_cols, key="demo_assets")
        extra, upload, base = [], None, "EUR"
    else:
        preset = sb.selectbox("Start from a preset", ["(custom)"] + list(PRESETS), key="preset")
        options = [i.symbol for i in CATALOG]
        labels = {i.symbol: f"{i.display} · {i.kind} · {i.name}" if i.short else f"{i.symbol} · {i.kind} · {i.name}"
                  for i in CATALOG}
        if preset != "(custom)" and st.session_state.get("_preset") != preset:
            st.session_state["catalog_assets"] = PRESETS[preset]
        st.session_state["_preset"] = preset
        chosen = sb.multiselect("ETFs, ETCs and index funds", options, format_func=lambda s: labels.get(s, s),
                                key="catalog_assets")
        extra_txt = sb.text_input("Other Yahoo tickers or ISINs (comma separated)", key="extra",
                                  placeholder="e.g. AAPL, IE00B3RBWM25, MEUD.PA")
        extra = [x.strip() for x in extra_txt.split(",") if x.strip()]
        up = sb.file_uploader("Your own NAV history (CSV)", type=["csv"], key="nav_csv",
                              help="First column = date, then one column per fund, prices in the base currency. "
                                   "Semicolons and decimal commas are fine.")
        upload = up.getvalue() if up is not None else None
        base = sb.selectbox("Base currency", ["EUR", "USD", "GBP", "CHF"], key="base",
                            help="Every price is converted to this currency with daily FX rates, so returns "
                                 "include the currency risk you actually bear.")

    with sb.expander("Period and data quality"):
        start = st.date_input("Start", key="start")
        end = st.date_input("End", key="end")
        backfill = st.checkbox("Backfill short fund histories with an ETF on the same index", key="backfill",
                               disabled=demo)
        clean = st.checkbox("Remove one-day bad prints", key="clean", disabled=demo)

    with sb.expander("Estimation", expanded=False):
        freq = st.selectbox("Return frequency", list(PERIODS_PER_YEAR), key="freq",
                            help="Weekly avoids the bias from exchanges closing at different times.")
        r_method = st.selectbox("Expected returns", list(RETURN_LABELS), format_func=RETURN_LABELS.get, key="r_method")
        c_method = st.selectbox("Covariance", list(COV_LABELS), format_func=COV_LABELS.get, key="c_method")
        rf = st.number_input("Risk-free rate (annual %)", step=0.25, key="rf",
                             help="Use the average short-term rate over the sample: about 1-2% for EUR since 2015.") / 100

    with sb.expander("Constraints", expanded=False):
        max_w = st.slider("Max weight per asset", 0.05, 1.0, step=0.05, key="max_w",
                          help="Caps stop the optimiser from betting everything on the asset with the luckiest past.")
        min_w = st.slider("Min weight per asset", 0.0, 0.2, step=0.01, key="min_w")
        st.caption("Asset-class limits (apply to Max Sharpe, Min variance, Max diversification):")
        group_df = st.data_editor(
            pd.DataFrame({"Class": list(ASSET_CLASSES) + ["Other"], "Min %": 0.0, "Max %": 100.0}),
            hide_index=True, key="groups", disabled=["Class"],
            column_config={"Min %": st.column_config.NumberColumn(min_value=0, max_value=100, step=5),
                           "Max %": st.column_config.NumberColumn(min_value=0, max_value=100, step=5)})

    return dict(demo=demo, chosen=chosen, extra=extra, upload=upload, base=base, start=start, end=end,
                backfill=backfill, clean=clean, freq=freq, r_method=r_method, c_method=c_method, rf=rf,
                max_w=max_w, min_w=min_w, group_df=group_df)


# =========================================================================== main
cfg = sidebar()
st.title("Portfolio Lab")

ids = list(dict.fromkeys(cfg["chosen"] + cfg["extra"]))
if not ids and not cfg["upload"]:
    st.info("Pick at least two assets in the sidebar to begin.")
    st.stop()

try:
    with st.spinner("Downloading prices and converting currencies..."):
        if cfg["demo"]:
            d = load_demo()
            data = PriceData(d.prices[ids], "EUR", {c: "EUR" for c in ids}, {c: c for c in ids})
        else:
            data = get_prices(tuple(ids), cfg["base"], cfg["backfill"], cfg["clean"], cfg["upload"])
except Exception as exc:  # network or data problem: tell the user what to do
    st.error(f"Could not load prices: {exc}")
    st.caption("Tip: switch to the offline demo dataset, or check the ticker on finance.yahoo.com.")
    st.stop()

for w in data.warnings:
    st.warning(w)
prices_all = data.prices.loc[pd.Timestamp(cfg["start"]):pd.Timestamp(cfg["end"])]
if prices_all.shape[1] < 2 or len(prices_all) < 60:
    st.error("Need at least two assets with a common history of 60+ days in the chosen period.")
    st.stop()

meta = {c: describe(c) for c in prices_all.columns}
label = {c: meta[c].display for c in prices_all.columns}
prices = prices_all.rename(columns=label)
assets = list(prices.columns)
inv_label = {v: k for k, v in label.items()}
asset_colors = charts.color_map(assets)
ccy = data.base_currency
ppy = PERIODS_PER_YEAR[cfg["freq"]]
returns = to_returns(prices, cfg["freq"])

# ---------------------------------------------------------------- instrument table (TER is editable)
inst_df = pd.DataFrame({
    "Asset": assets,
    "Name": [meta[inv_label[a]].name for a in assets],
    "Type": [meta[inv_label[a]].kind for a in assets],
    "Class": [meta[inv_label[a]].asset_class for a in assets],
    "Quote ccy": [data.currencies.get(inv_label[a], ccy) for a in assets],
    "TER %": [meta[inv_label[a]].ter * 100 for a in assets],
    "Backfilled with": [data.backfilled.get(inv_label[a], "") for a in assets],
    "Yahoo symbol": [data.resolved.get(inv_label[a], inv_label[a]) for a in assets],
})

tabs = st.tabs(["Overview", "Optimiser", "My portfolio", "Backtest", "Monte Carlo", "Methodology"])

with tabs[0]:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Assets", len(assets))
    c2.metric("Period", f"{prices.index[0]:%b %Y} to {prices.index[-1]:%b %Y}")
    c3.metric("Years of data", f"{(prices.index[-1] - prices.index[0]).days / 365.25:.1f}")
    c4.metric("Return observations", f"{len(returns)} {cfg['freq']}")
    st.subheader("Instruments")
    st.caption("TER values are indicative. Edit them here and every cost calculation updates.")
    inst_df = st.data_editor(inst_df, hide_index=True, key="inst", disabled=[c for c in inst_df.columns if c != "TER %"],
                             column_config={"TER %": st.column_config.NumberColumn(format="%.3f", min_value=0.0,
                                                                                   max_value=3.0, step=0.01)})
ter = pd.Series(inst_df["TER %"].values / 100, index=assets)
classes = dict(zip(assets, inst_df["Class"]))

# ---------------------------------------------------------------- estimation and optimisation
mu_est, cov, est_info = get_estimates(returns, ppy, cfg["r_method"], cfg["c_method"])
groups = []
for _, row in cfg["group_df"].iterrows():
    members = [a for a in assets if classes[a] == row["Class"] or (row["Class"] == "Other" and classes[a] not in ASSET_CLASSES)]
    if members and (row["Min %"] > 0 or row["Max %"] < 100):
        groups.append(GroupLimit(row["Class"], members, row["Min %"] / 100, row["Max %"] / 100))
max_w = max(cfg["max_w"], 1.0 / len(assets) + 1e-6)
spec = json.dumps({"lower": {a: cfg["min_w"] for a in assets}, "upper": {}, "default_upper": max_w,
                   "groups": [g.__dict__ for g in groups]})
if cfg["max_w"] < 1.0 / len(assets):
    st.info(f"Max weight raised to {max_w:.0%}: with {len(assets)} assets a lower cap cannot add up to 100%.")

with tabs[1]:
    with st.expander("Use your own return assumptions (capital market assumptions)"):
        st.caption("Historical means are very noisy. You can type your own forward-looking expected returns, "
                   "e.g. 6-7% for global equities, 2.5-3% for euro government bonds.")
        mu_df = st.data_editor(pd.DataFrame({"Asset": assets, "Estimated %": (mu_est.values * 100).round(2),
                                             "Std. error %": (est_info["se"].values * 100).round(2),
                                             "Use %": (mu_est.values * 100).round(2)}),
                               hide_index=True, key="mu_edit", disabled=["Asset", "Estimated %", "Std. error %"])
mu = pd.Series(mu_df["Use %"].astype(float).values / 100, index=assets)

try:
    portfolios, frontier = get_portfolios(mu, cov, cfg["rf"], spec)
except InfeasibleError as exc:
    st.error(f"Constraints are infeasible: {exc}")
    st.stop()

# ---------------------------------------------------------------- my portfolio (computed early, shown in its tab)
with tabs[2]:
    st.subheader("Your current positions")
    st.caption("Enter the market value of each position (and what you paid, for the tax estimate). "
               "Leave zeros for assets you do not own.")
    seed = st.session_state.get("holdings_seed", {})
    hold_df = st.data_editor(
        pd.DataFrame({"Asset": assets,
                      "Value": [float(seed.get(a, {}).get("value", 0.0)) for a in assets],
                      "Cost basis": [float(seed.get(a, {}).get("cost", 0.0)) for a in assets]}),
        hide_index=True, key="holdings", disabled=["Asset"],
        column_config={"Value": st.column_config.NumberColumn(f"Market value ({ccy})", min_value=0.0, step=100.0,
                                                              format="%.2f"),
                       "Cost basis": st.column_config.NumberColumn(f"Cost basis ({ccy})", min_value=0.0, step=100.0,
                                                                   format="%.2f")})
holdings = [Holding(a, float(v or 0.0), float(c or 0.0))
            for a, v, c in zip(hold_df["Asset"], hold_df["Value"], hold_df["Cost basis"])]
has_holdings = sum(h.value for h in holdings) > 0
opt_eval = PortfolioOptimizer(mu, cov, cfg["rf"])
if has_holdings:
    my_w = pd.Series({h.asset: h.value for h in holdings}).reindex(assets).fillna(0.0)
    my_w = my_w / my_w.sum()
    portfolios = {**portfolios, "My portfolio": opt_eval.evaluate(my_w.values, "My portfolio")}

# =========================================================================== Overview tab
with tabs[0]:
    stats = M.summary_table(prices.pct_change().dropna(), 252, cfg["rf"])
    stats.insert(0, "TER", ter)
    st.subheader(f"Historical performance (daily data, in {ccy})")
    st.dataframe(stats.style.format({c: "{:.2%}" for c in stats.columns if c not in
                                     ("Sharpe", "Sortino", "Calmar", "Longest drawdown (days)")} |
                                    {"Sharpe": "{:.2f}", "Sortino": "{:.2f}", "Calmar": "{:.2f}",
                                     "Longest drawdown (days)": "{:.0f}", "TER": "{:.2%}"}), width="stretch")
    log = st.toggle("Log scale", value=True, key="log_overview")
    st.plotly_chart(charts.growth_chart(prices / prices.iloc[0] * 100, asset_colors, log, "Growth of 100"),
                    width="stretch")
    st.plotly_chart(charts.drawdown_chart(prices, asset_colors), width="stretch")
    a, b = st.columns([1, 1])
    with a:
        st.subheader("Correlation")
        st.caption(f"{cfg['freq'].capitalize()} returns, from the {COV_LABELS[cfg['c_method']].split(' (')[0]} estimate.")
        st.plotly_chart(charts.correlation_heatmap(estimators.cov_to_corr(cov)), width="stretch")
    with b:
        st.subheader("Calendar-year returns")
        st.plotly_chart(charts.calendar_heatmap(M.calendar_year_returns(prices)), width="stretch")
    with st.expander("Instrument details"):
        for a_ in assets:
            m = meta[inv_label[a_]]
            if m.note:
                st.markdown(f"**{a_}**: {m.note}")
        st.dataframe(inst_df, hide_index=True, width="stretch")

# =========================================================================== Optimiser tab
with tabs[1]:
    info = []
    if est_info["phi"] is not None:
        info.append(f"Bayes-Stein pulled the means {est_info['phi']:.0%} of the way towards the common mean.")
    if est_info["delta"] is not None:
        info.append(f"Ledoit-Wolf shrinkage intensity: {est_info['delta']:.0%}.")
    if info:
        st.caption(" ".join(info))

    c1, c2 = st.columns([3, 1])
    with c2:
        st.markdown("**Build your own point on the frontier**")
        gmv_vol = portfolios["Minimum variance"].volatility
        top_vol = max(p.volatility for p in frontier)
        lo_v, hi_v = float(np.ceil(gmv_vol * 1000) / 1000), float(np.floor(top_vol * 1000) / 1000)
        hi_v = max(hi_v, lo_v + 0.001)
        target_vol = st.slider("Target volatility", lo_v, hi_v, float(round((lo_v + hi_v) / 2, 3)), 0.001,
                               format="%.3f")
        try:
            custom = PortfolioOptimizer(mu, cov, cfg["rf"], _constraints_from_json(spec)).efficient_risk(target_vol)
            custom.name = "Target volatility"
            st.metric("Expected return", pct(custom.expected_return))
            st.metric("Sharpe", f"{custom.sharpe:.2f}")
        except (InfeasibleError, RuntimeError) as exc:
            custom = None
            st.warning(str(exc))
        show_cloud = st.toggle("Show random portfolios", value=True, key="cloud")
    shown = dict(portfolios)
    if custom is not None:
        shown["Target volatility"] = custom
    with c1:
        st.plotly_chart(charts.efficient_frontier(
            frontier, shown, mu, pd.Series(np.sqrt(np.diag(cov.values)), index=assets), cfg["rf"],
            get_cloud(mu, cov) if show_cloud else None, asset_colors), width="stretch")

    rows = []
    for name, p in shown.items():
        rows.append({"Portfolio": name, "Expected return": p.expected_return, "Volatility": p.volatility,
                     "Sharpe": p.sharpe, "TER": float(p.weights @ ter), "Effective N": effective_n(p.weights),
                     "Diversification ratio": diversification_ratio(p.weights, cov),
                     "Largest weight": float(p.weights.max()),
                     "Honours constraints": "yes" if name in CONSTRAINED or name == "Target volatility" else "no"})
    table = pd.DataFrame(rows).set_index("Portfolio")
    st.subheader("Strategy comparison (in-sample)")
    st.dataframe(table.style.format({"Expected return": "{:.2%}", "Volatility": "{:.2%}", "Sharpe": "{:.2f}",
                                     "TER": "{:.3%}", "Effective N": "{:.1f}", "Diversification ratio": "{:.2f}",
                                     "Largest weight": "{:.1%}"}), width="stretch")
    st.caption("In-sample numbers flatter every optimised portfolio because they are fitted to the same data. "
               "Check the Backtest tab for out-of-sample results.")

    st.subheader("Weights")
    pick = st.multiselect("Portfolios", list(shown), default=[n for n in ("Maximum Sharpe", "Risk parity", "HRP",
                          "My portfolio") if n in shown], key=f"w_pick_{len(shown)}")
    if pick:
        wdf = pd.DataFrame({n: shown[n].weights for n in pick})
        st.plotly_chart(charts.weights_bars(wdf, charts.color_map(list(shown))), width="stretch")
        st.download_button("Download weights (CSV)", wdf.to_csv().encode(), "weights.csv", "text/csv")

    st.subheader("Where does the risk come from?")
    focus = st.selectbox("Portfolio", list(shown), key=f"rc_pick_{len(shown)}")
    rc = risk_contributions(shown[focus].weights, cov)
    st.plotly_chart(charts.risk_vs_weight(shown[focus].weights, rc), width="stretch")
    st.caption("Risk contribution = share of portfolio variance coming from each asset. "
               "In a typical 60/40 portfolio equities bring around 90% of the risk.")

# =========================================================================== My portfolio tab
with tabs[2]:
    if not has_holdings:
        st.info("Enter your positions above to compare them with the optimised portfolios and plan a rebalance.")
    else:
        me = portfolios["My portfolio"]
        total = sum(h.value for h in holdings)
        cost_total = sum(h.cost_basis for h in holdings)
        k = st.columns(5)
        k[0].metric("Portfolio value", money(total, ccy))
        k[1].metric("Unrealised gain", money(total - cost_total, ccy) if cost_total else "n/a",
                    pct(total / cost_total - 1) if cost_total else None)
        k[2].metric("Expected return", pct(me.expected_return))
        k[3].metric("Volatility", pct(me.volatility))
        k[4].metric("Annual cost (TER)", f"{money(float(me.weights @ ter) * total, ccy)} ({pct(float(me.weights @ ter), 2)})")

        same_risk = None
        try:
            same_risk = PortfolioOptimizer(mu, cov, cfg["rf"], _constraints_from_json(spec)).efficient_risk(me.volatility)
        except (InfeasibleError, RuntimeError):
            pass
        if same_risk is not None:
            gain = same_risk.expected_return - me.expected_return
            st.markdown(f"With the same volatility ({pct(me.volatility)}), the efficient portfolio would expect "
                        f"**{pct(same_risk.expected_return)}** a year, {pct(gain, 2)} more than yours "
                        f"(about {money(gain * total, ccy)} a year on your current balance, before costs).")

        st.subheader("Rebalancing plan")
        c1, c2, c3 = st.columns(3)
        target_name = c1.selectbox("Target portfolio", [n for n in shown if n != "My portfolio"], key="target_pick")
        new_cash = c2.number_input(f"New money to invest ({ccy})", value=1000.0, step=100.0, key="new_cash")
        sells = c3.toggle("Allow selling (full rebalance)", value=False, key="sells",
                          help="Off: only the new money is used, nothing is sold and no tax is triggered.")
        target_w = shown[target_name].weights
        fund_flags = {a: meta[inv_label[a]].is_fund for a in assets}
        try:
            plan = rebalance_plan(holdings, target_w, new_cash, allow_sells=sells, is_fund=fund_flags)
        except ValueError as exc:
            st.error(str(exc))
            plan = None
        if plan is not None:
            st.dataframe(plan.style.format({"Current value": "{:,.2f}", "Trade": "{:+,.2f}", "Value after": "{:,.2f}",
                                            "Realised gain": "{:,.2f}", "Estimated tax": "{:,.2f}",
                                            "Current weight": "{:.1%}", "Target weight": "{:.1%}",
                                            "Weight after": "{:.1%}"}), width="stretch")
            before_gap = tracking_gap(me.weights, target_w)
            after_gap = tracking_gap(plan["Weight after"], target_w)
            k = st.columns(3)
            k[0].metric("Distance to target before", pct(before_gap))
            k[1].metric("Distance to target after", pct(after_gap))
            k[2].metric("Estimated Spanish tax (IRPF)", money(plan["Estimated tax"].sum(), ccy))
            st.caption("Tax: savings-base brackets 19% to 30% on realised gains, average-cost method, no loss "
                       "offsetting. Index-fund sales are assumed to go by traspaso (tax-deferred). Order of magnitude "
                       "only, not tax advice.")

    st.divider()
    st.subheader("Save this session")
    st.caption("Downloads your universe, settings and holdings so you can load them next time from the sidebar.")
    widget_keys = [k_ for k_ in DEFAULTS if k_ not in ("start", "end")] + ["demo_assets"]
    payload = {"widgets": {k_: st.session_state[k_] for k_ in widget_keys if k_ in st.session_state},
               "holdings": {h.asset: {"value": h.value, "cost": h.cost_basis} for h in holdings if h.value or h.cost_basis}}
    st.download_button("Download session (.json)", json.dumps(payload, indent=2, default=str).encode(),
                       "portfolio_session.json", "application/json")

# =========================================================================== Backtest tab
with tabs[3]:
    st.caption("Walk-forward: at every rebalance date each strategy is re-optimised using only the past "
               "`lookback` years, then held until the next date. Costs and TERs are deducted.")
    c = st.columns(5)
    lookback = c[0].slider("Lookback (years)", 1.0, 5.0, 3.0, 0.5, key="lookback")
    rebalance = c[1].selectbox("Rebalance", [r for r in REBALANCE_RULES if r != "Never"], index=1, key="rebal")
    cost_bps = c[2].number_input("Trading cost (bps)", 0.0, 100.0, 10.0, 1.0, key="cost_bps")
    apply_ter = c[3].toggle("Deduct TER", value=True, key="apply_ter")
    bench = c[4].selectbox("Benchmark", assets, index=0, key="bench")
    default_bt = ["Maximum Sharpe", "Risk parity", "Equal weight"] + (["My portfolio"] if has_holdings else [])
    chosen_bt = st.multiselect("Strategies", list(STRATEGIES) + (["My portfolio"] if has_holdings else []),
                               default=default_bt, key=f"bt_pick_{has_holdings}")
    bt_start = lookback_start(prices, lookback)
    if bt_start >= prices.index[-1] - pd.Timedelta(days=365):
        st.warning("Not enough history for this lookback. Shorten it or pick assets with longer histories.")
    elif chosen_bt:
        results = {}
        with st.spinner("Running walk-forward backtests..."):
            for name in chosen_bt:
                kind = "static" if name in ("My portfolio", "Equal weight") else "dynamic"
                w = portfolios[name].weights if name in portfolios and kind == "static" else None
                results[name] = get_backtest(prices, kind, name, w, rebalance, bt_start, cost_bps,
                                             ter if apply_ter else None, lookback, cfg["freq"], cfg["r_method"],
                                             cfg["c_method"], cfg["rf"], spec)
            bench_w = pd.Series(0.0, index=assets)
            bench_w[bench] = 1.0
            results[f"{bench} (buy and hold)"] = get_backtest(prices, "static", f"{bench} (buy and hold)", bench_w,
                                                              "Never", bt_start, cost_bps, ter if apply_ter else None,
                                                              lookback, cfg["freq"], cfg["r_method"], cfg["c_method"],
                                                              cfg["rf"], spec)
        wealth = pd.DataFrame({n: r.wealth for n, r in results.items()})
        colors = charts.color_map(list(wealth.columns))
        st.plotly_chart(charts.growth_chart(wealth * 100, colors, False, "Growth of 100, out-of-sample"),
                        width="stretch")
        st.plotly_chart(charts.drawdown_chart(wealth, colors), width="stretch")
        bench_r = wealth[f"{bench} (buy and hold)"].pct_change().dropna()
        rows = {}
        for n in wealth.columns:
            s = M.summary(wealth[n].pct_change().dropna(), 252, cfg["rf"], bench_r)
            s["Avg turnover / rebalance"] = float(results[n].turnover.iloc[1:].mean()) if len(results[n].turnover) > 1 else 0.0
            rows[n] = s
        bt_table = pd.DataFrame(rows).T
        fmt = {c_: "{:.2%}" for c_ in bt_table.columns}
        fmt.update({k_: "{:.2f}" for k_ in ("Sharpe", "Sortino", "Calmar", "Beta", "Correlation", "Information ratio")})
        fmt["Longest drawdown (days)"] = "{:.0f}"
        st.dataframe(bt_table.style.format(fmt, na_rep="-"), width="stretch")
        st.subheader("Calendar-year returns")
        st.plotly_chart(charts.calendar_heatmap(M.calendar_year_returns(wealth)), width="stretch")
        dyn = [n for n in chosen_bt if n not in ("My portfolio", "Equal weight")]
        if dyn:
            which = st.selectbox("Weights over time", dyn, key="wot")
            st.plotly_chart(charts.weights_over_time(results[which].weights, asset_colors), width="stretch")

def render_simulation(sim, inp, goal, monthly, monthly_hist):
    real = st.toggle("Show in today's money (inflation-adjusted)", value=True, key="mc_real")
    summ = sim.summary()
    k = st.columns(5)
    k[0].metric("Median outcome", money(float(np.median(sim.final(real))), ccy))
    k[1].metric("Bad case (P5)", money(float(np.percentile(sim.final(real), 5)), ccy))
    k[2].metric("Good case (P95)", money(float(np.percentile(sim.final(real), 95)), ccy))
    k[3].metric("Money contributed", money(float(sim.contributed[-1]), ccy))
    if goal:
        k[4].metric("Chance of reaching the goal", pct(summ["Probability of reaching the goal"], 0))
    elif monthly < 0:
        k[4].metric("Chance of running out", pct(summ["Probability of ruin"], 0))
    else:
        k[4].metric("Chance of ending below contributions", pct(summ["Probability of ending below contributions"], 0))

    pct_df = sim.percentiles(real)
    contributed = sim.contributed / (sim.deflator if real else 1.0)
    rng = np.random.default_rng(0)
    sample = sim.paths[rng.choice(len(sim.paths), size=min(30, len(sim.paths)), replace=False)]
    if real:
        sample = sample / sim.deflator
    st.plotly_chart(charts.fan_chart(pct_df, contributed, goal or None, sample), width="stretch")
    a, b = st.columns([3, 2])
    with a:
        st.markdown("**Distribution of the final value**")
        st.plotly_chart(charts.final_histogram(sim.final(real), float(contributed[-1]), goal or None), width="stretch")
    with b:
        st.markdown("**Milestones**")
        marks = sorted({y for y in (1, 3, 5, 10, 15, 20, 25, 30, 40, 50) if y <= years} | {years})
        ms = pct_df.iloc[[m * 12 for m in marks]].copy()
        ms.index = [f"Year {m}" for m in marks]
        ms.insert(0, "Contributed", contributed[[m * 12 for m in marks]])
        st.dataframe(ms.style.format("{:,.0f}"), width="stretch")
        st.caption(f"Median worst drawdown along the way: {pct(summ['Median worst drawdown'])}.")
    if goal:
        if st.button("How much should I contribute each month to reach the goal?", key="solve"):
            with st.spinner("Solving..."):
                res = {conf: required_contribution(inp, goal, conf, monthly_hist) for conf in (0.5, 0.75, 0.9)}
            st.table(pd.DataFrame({"Probability of success": ["50%", "75%", "90%"],
                                   f"Monthly contribution ({ccy})": [f"{v:,.0f}" for v in res.values()]}))



# =========================================================================== Monte Carlo tab
with tabs[4]:
    options = list(shown)
    default_idx = options.index("My portfolio") if "My portfolio" in options else 0
    c = st.columns(4)
    mc_name = c[0].selectbox("Portfolio", options, index=default_idx, key=f"mc_pick_{len(options)}")
    p = shown[mc_name]
    start_val = float(sum(h.value for h in holdings)) if has_holdings else 10_000.0
    initial = c[1].number_input(f"Initial capital ({ccy})", 0.0, 1e9, start_val, 1000.0, key=f"mc_init_{start_val:.0f}")
    monthly = c[2].number_input(f"Monthly contribution ({ccy})", -1e6, 1e6, 300.0, 50.0, key="mc_month",
                                help="Negative = monthly withdrawal (retirement phase).")
    years = c[3].slider("Horizon (years)", 1, 50, 20, key="mc_years")

    c = st.columns(4)
    exp_r = c[0].number_input("Expected return (annual %)", -20.0, 40.0, round(p.expected_return * 100, 2), 0.25,
                              help="Prefilled with the model estimate. Past returns rarely repeat: "
                                   "consider something more conservative.") / 100
    vol = c[1].number_input("Volatility (annual %)", 0.0, 100.0, round(p.volatility * 100, 2), 0.25) / 100
    fee = c[2].number_input("Annual costs (%)", 0.0, 5.0, round(float(p.weights @ ter) * 100, 3), 0.05,
                            help="Weighted TER plus any platform fee.") / 100
    infl = c[3].number_input("Inflation (annual %)", -2.0, 15.0, 2.0, 0.25, key="mc_infl") / 100
    if exp_r > 0.08:
        st.caption(f"Heads-up: {exp_r:.1%} a year is above the long-run nominal return of global equities "
                   "(roughly 6-8%). Historical estimates from a strong decade tend to overstate the future.")

    c = st.columns(4)
    method = c[0].selectbox("Return model", METHODS, key="mc_method",
                            format_func={"lognormal": "Log-normal", "student_t": "Student-t (fat tails)",
                                         "bootstrap": "Historical block bootstrap"}.get)
    growth = c[1].number_input("Contribution growth (annual %)", 0.0, 20.0, 0.0, 0.5, key="mc_growth") / 100
    goal = c[2].number_input(f"Goal in today's money ({ccy}, 0 = none)", 0.0, 1e10, 0.0, 10_000.0, key="mc_goal")
    n_sims = c[3].select_slider("Simulations", [1000, 2000, 5000, 10000, 20000], value=5000, key="mc_n")

    monthly_hist = (to_returns(prices, "monthly") @ p.weights.reindex(assets).fillna(0).values)
    inp = SimulationInput(initial=initial, monthly_contribution=monthly, contribution_growth=growth, years=years,
                          expected_return=exp_r, volatility=vol, annual_fee=fee, inflation=infl, method=method,
                          n_sims=int(n_sims), target=goal or None)
    try:
        sim = simulate(inp, history=monthly_hist)
    except ValueError as exc:
        st.error(str(exc))
        sim = None
    if sim is not None:
        render_simulation(sim, inp, goal, monthly, monthly_hist)

# =========================================================================== Methodology tab
with tabs[5]:
    st.markdown(r"""
### What the app does

1. **Data.** Total-return prices (dividends reinvested) from Yahoo Finance. ISINs are resolved automatically, prices in
   GBp are converted to GBP, and every series is converted to the base currency with daily FX rates, so the
   currency risk you really bear is part of the analysis. Index funds with short Yahoo histories can be backfilled
   with an ETF that tracks the same index.
2. **Estimation.** Returns at weekly frequency by default (daily closes on different exchanges are not synchronous).
   Expected returns use the Bayes-Stein estimator (Jorion, 1986) and the covariance uses Ledoit-Wolf shrinkage
   towards constant correlation (Ledoit and Wolf, 2004).
3. **Optimisation.** For weights $w$, expected returns $\mu$ and covariance $\Sigma$:

$$\mu_p = w^\top \mu, \qquad \sigma_p^2 = w^\top \Sigma w, \qquad S = \frac{\mu_p - r_f}{\sigma_p}$$

   * *Minimum variance*: $\min_w w^\top \Sigma w$ subject to $\mathbf{1}^\top w = 1$, bounds and group limits.
   * *Maximum Sharpe*: not convex as written; with $y = \kappa w$ it becomes the convex problem
     $\min_y y^\top \Sigma y$ s.t. $(\mu - r_f)^\top y = 1$, $\ell\kappa \le y \le u\kappa$, so the global optimum is found.
   * *Maximum diversification*: same trick with $\sigma$ instead of $\mu - r_f$.
   * *Risk parity*: $\min_y \tfrac12 y^\top \Sigma y - \sum_i b_i \ln y_i$, which equalises
     $RC_i = w_i (\Sigma w)_i / \sigma_p^2$.
   * *HRP*: hierarchical clustering on $d_{ij} = \sqrt{(1-\rho_{ij})/2}$ and recursive bisection (Lopez de Prado, 2016).
4. **Backtest.** Walk-forward: every rebalance only uses past data. Transaction costs and TERs are deducted.
5. **Monte Carlo.** Monthly steps, log-normal (moment-matched), Student-t or block bootstrap of real months, with
   contributions or withdrawals, inflation and fees.

**Read the results with care.** Expected returns cannot be estimated precisely from a few years of data; the
standard error is shown next to each estimate. Treat the optimiser as a tool to understand trade-offs, not as a
crystal ball. This is not financial advice.
""")
    st.markdown("A longer illustrated explanation lives in `docs/guide.html` in the repository.")
