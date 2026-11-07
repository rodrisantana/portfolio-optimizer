"""Portfolio Lab: optimise, backtest and plan a portfolio of ETFs, ETCs, index funds and active funds.

Run with:  streamlit run app.py          (add ?lang=en to the URL for English)
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import date

import numpy as np
import pandas as pd
import streamlit as st

from portfolio_optimizer import charts, estimators, i18n
from portfolio_optimizer import metrics as M
from portfolio_optimizer.assumptions import DEFAULT_CMA, long_term_returns
from portfolio_optimizer.backtest import REBALANCE_RULES, lookback_start, run_backtest, static_weights, walk_forward
from portfolio_optimizer.breakdown import DIMENSIONS, breakdown_table
from portfolio_optimizer.catalog import (
    ASSET_CLASSES,
    CATALOG,
    EQUITY,
    FIXED_INCOME,
    KINDS,
    MANAGEMENT,
    MIXED,
    PRESETS,
    REGIONS,
    Instrument,
    describe,
    is_isin,
    parse_proxy,
    register,
)
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
from portfolio_optimizer.planning import historical_dca, projection_table

st.set_page_config(page_title="Portfolio Lab", page_icon="📈", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
.block-container {padding-top: 2rem; max-width: 1400px;}
[data-testid="stMetricValue"] {font-size: 1.5rem;}
[data-testid="stMetric"] {background: rgba(137,135,129,0.07); border-radius: 10px; padding: 12px 14px;}
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------------- language
qp_lang = st.query_params.get("lang")
if "_lang_next" in st.session_state:                   # a loaded session asks for its language
    st.session_state["lang"] = st.session_state.pop("_lang_next")
st.session_state.setdefault("lang", qp_lang if qp_lang in ("es", "en") else "es")
lang = st.sidebar.segmented_control("Idioma / Language", ["es", "en"], key="lang", required=True,
                                    format_func={"es": "Español", "en": "English"}.get)
if st.query_params.get("lang") != lang:
    st.query_params["lang"] = lang
i18n.set_language(lang)
t = i18n.t
charts.set_translator(t)

RETURN_METHODS = {"long_term": "Long-term forecasts (recommended)", "bayes_stein": "Bayes-Stein shrinkage of history",
                  "historical": "Historical mean", "ewma": "Exponentially weighted mean"}
COV_METHODS = {"ledoit_wolf": "Ledoit-Wolf shrinkage (recommended)", "sample": "Sample covariance",
               "ewma": "Exponentially weighted (RiskMetrics)"}
CURRENCY_SYMBOL = {"EUR": "€", "USD": "$", "GBP": "£", "CHF": "CHF"}


def pct(x: float, d: int = 1) -> str:
    if x is None or not np.isfinite(x):
        return "n/a"
    s = f"{x * 100:.{d}f}"
    return (s.replace(".", ",") + " %") if lang == "es" else s + "%"


def money(x: float, ccy: str) -> str:
    sym = CURRENCY_SYMBOL.get(ccy, ccy)
    if lang == "es":
        return f"{x:,.0f}".replace(",", ".") + f" {sym}"
    return f"{sym}{x:,.0f}"


def styled(df: pd.DataFrame, fmt, **kw):
    """Styler with Spanish separators (1.234,56) when the interface is in Spanish."""
    if lang == "es":
        kw.update(decimal=",", thousands=".")
    return df.style.format(fmt, **kw)


def tr_index(df: pd.DataFrame | pd.Series) -> pd.DataFrame | pd.Series:
    return df.rename(index=lambda v: t(v) if isinstance(v, str) else v)


def tr_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns=lambda v: t(v) if isinstance(v, str) else v)


# =========================================================================== cached computations
@st.cache_data(show_spinner=False, ttl=6 * 3600)
def get_prices(ids: tuple[str, ...], base: str, backfill: bool, clean: bool, upload: bytes | None,
               custom_spec: str) -> PriceData:
    for spec in json.loads(custom_spec):                 # make user funds known inside the cached call too
        register(Instrument(**{**spec, "exposure": tuple(map(tuple, spec.get("exposure", ())))}))
    uploaded = parse_uploaded_csv(upload) if upload else None
    return load_prices(list(ids), base, backfill=backfill, clean_spikes=clean, uploaded=uploaded)


@st.cache_data(show_spinner=False)
def get_estimates(returns: pd.DataFrame, ppy: int, c_method: str):
    if c_method == "ledoit_wolf":
        cov, delta = estimators.ledoit_wolf_cov(returns, ppy)
    else:
        cov, delta = estimators.covariance(returns, ppy, c_method), None
    hist = {m: estimators.expected_returns(returns, ppy, m) for m in ("historical", "bayes_stein", "ewma")}
    phi = estimators.bayes_stein_mean(returns, ppy)[1]
    return estimators.nearest_psd(cov), hist, {"delta": delta, "phi": phi,
                                              "se": estimators.mean_standard_error(returns, ppy)}


def _constraints_from_json(spec: str) -> Constraints:
    d = json.loads(spec)
    return Constraints(lower=d["lower"], upper=d["upper"], default_upper=d["default_upper"],
                       groups=[GroupLimit(**g) for g in d["groups"]])


@st.cache_data(show_spinner=False)
def get_portfolios(mu: pd.Series, cov: pd.DataFrame, rf: float, spec: str, n_points: int = 60):
    opt = PortfolioOptimizer(mu, cov, rf, _constraints_from_json(spec))
    return opt.standard_portfolios(), opt.efficient_frontier(n_points)


@st.cache_data(show_spinner=False)
def get_cloud(mu: pd.Series, cov: pd.DataFrame) -> pd.DataFrame:
    return random_portfolios(mu, cov, 2500)


@st.cache_data(show_spinner=False)
def get_backtest(prices: pd.DataFrame, kind: str, name: str, weights: pd.Series | None, rebalance: str,
                 start: pd.Timestamp, cost_bps: float, lookback: float, freq: str, r_method: str, c_method: str,
                 rf: float, spec: str):
    if kind == "static":
        fn = static_weights(weights)
    else:
        method = "bayes_stein" if r_method == "long_term" else r_method   # forecasts are not point-in-time
        fn = walk_forward(name, lookback, freq, method, c_method, rf, _constraints_from_json(spec))
    return run_backtest(prices, fn, name, rebalance, start=start, cost_bps=cost_bps)


# =========================================================================== sidebar
DEFAULTS = {
    "source": "live", "preset": "(custom)",
    "catalog_assets": PRESETS["Boglehead core (world + EM + bonds + gold)"], "extra": "", "base": "EUR",
    "start": date(2015, 1, 1), "end": date.today(), "backfill": True, "clean": True,
    "freq": "weekly", "r_method": "long_term", "c_method": "ledoit_wolf", "rf": 2.0, "max_w": 0.5, "min_w": 0.0,
    "alpha": 0.0,
}
CUSTOM_COLUMNS = ["Name", "ISIN or ticker", "Proxy", "TER %", "Class", "Region", "Management"]


def custom_instruments(df: pd.DataFrame) -> list[Instrument]:
    """Turn the 'add your own fund' table into catalogue instruments."""
    out = []
    for _, r in df.iterrows():
        name = str(r.get("Name") or "").strip()
        code = str(r.get("ISIN or ticker") or "").strip().upper()
        proxy = str(r.get("Proxy") or "").strip().upper()
        if not (name or code) or not (code or proxy):
            continue
        try:
            if proxy:
                parse_proxy(proxy)
        except ValueError:
            continue
        cls = i18n.untranslate(str(r.get("Class") or "Equity"))
        mgmt = i18n.untranslate(str(r.get("Management") or "Passive"))
        region = i18n.untranslate(str(r.get("Region") or "Global"))
        exposure = ((EQUITY, 0.5), (FIXED_INCOME, 0.5)) if cls == MIXED else ()
        kind = "Active fund" if mgmt == "Active" else ("Index fund" if is_isin(code) or not code else "ETF")
        symbol = code or name
        ter = float(r.get("TER %") or 0.0) / 100
        out.append(Instrument(symbol, name or code, kind, cls, ter, code if is_isin(code) else "", region,
                              "Broad", mgmt, proxy, exposure, short=(name or code)[:28]))
    return out


def sidebar():
    for k_, v_ in DEFAULTS.items():
        st.session_state.setdefault(k_, v_)
    sb = st.sidebar
    sb.title("Portfolio Lab")
    sb.caption(t("Optimisation, backtests and savings plans for ETFs, ETCs, index funds and active funds."))

    session = sb.file_uploader(t("Load a saved session (.json)"), type=["json"], key="session_file",
                               help=t("Restores your universe, holdings and settings."))
    if session is not None and st.session_state.get("_loaded") != session.file_id:
        cfg = json.loads(session.getvalue())
        for k, v in cfg.get("widgets", {}).items():
            if k == "lang":
                st.session_state["_lang_next"] = v
                continue
            if k == "source" and v not in ("live", "demo"):
                v = "demo" if "demo" in str(v).lower() else "live"
            st.session_state[k] = v
        st.session_state["holdings_seed"] = cfg.get("holdings", {})
        st.session_state["custom_seed"] = cfg.get("custom_funds", [])
        for stale in ("holdings", "inst", "mu_edit", "groups", "custom_funds", "cma_edit"):
            st.session_state.pop(stale, None)
        st.session_state["_loaded"] = session.file_id
        st.rerun()

    source = sb.radio(t("Data source"), ["live", "demo"], key="source",
                      format_func={"live": t("Yahoo Finance (live)"), "demo": t("Offline demo dataset")}.get,
                      help=t("The demo dataset ships with the repo (8 UCITS products in EUR, 2018-2026) and works "
                             "without internet."))
    demo = source == "demo"
    customs: list[Instrument] = []
    if demo:
        demo_cols = list(load_demo().prices.columns)
        st.session_state.setdefault("demo_assets", [c for c in demo_cols if c != "XEON.DE"])
        chosen = sb.multiselect(t("Assets"), demo_cols, key="demo_assets")
        extra, upload, base = [], None, "EUR"
    else:
        preset = sb.selectbox(t("Start from a preset"), ["(custom)"] + list(PRESETS), key="preset", format_func=t)
        options = [i.symbol for i in CATALOG]
        labels = {i.symbol: f"{i.display} · {t(i.kind)} · {i.name}" for i in CATALOG}
        if preset != "(custom)" and st.session_state.get("_preset") != preset:
            st.session_state["catalog_assets"] = PRESETS[preset]
        st.session_state["_preset"] = preset
        chosen = sb.multiselect(t("ETFs, ETCs, index funds and active funds"), options,
                                format_func=lambda s: labels.get(s, s), key="catalog_assets")
        extra_txt = sb.text_input(t("Other Yahoo tickers or ISINs (comma separated)"), key="extra",
                                  placeholder="AAPL, IE00B3RBWM25, MEUD.PA")
        extra = [x.strip() for x in extra_txt.split(",") if x.strip()]
        with sb.expander(t("Add a fund that is not on the list")):
            st.caption(t("For funds Yahoo does not cover well (for example an Amundi fund bought at Openbank). "
                         "Give the ISIN if you have it and an ETF that follows the same index as proxy: real prices "
                         "are used when they exist, otherwise the fund is simulated as the proxy minus the fee "
                         "difference. A blend works too: EUNL.DE:0.6,EUNA.DE:0.4"))
            seed = pd.DataFrame(st.session_state.get("custom_seed") or [], columns=CUSTOM_COLUMNS)
            seed["TER %"] = pd.to_numeric(seed["TER %"], errors="coerce")
            custom_df = st.data_editor(
                seed, num_rows="dynamic", key="custom_funds", hide_index=True,
                column_config={
                    "Name": st.column_config.TextColumn(t("Name")),
                    "ISIN or ticker": st.column_config.TextColumn(t("ISIN or ticker")),
                    "Proxy": st.column_config.TextColumn(t("Proxy"), help="EUNL.DE"),
                    "TER %": st.column_config.NumberColumn("TER %", min_value=0.0, max_value=5.0, step=0.05),
                    "Class": st.column_config.SelectboxColumn(t("Class"), options=[t(c) for c in ASSET_CLASSES + (MIXED,)]),
                    "Region": st.column_config.SelectboxColumn(t("Region"), options=[t(r) for r in REGIONS]),
                    "Management": st.column_config.SelectboxColumn(t("Management"), options=[t(m) for m in MANAGEMENT]),
                })
            customs = custom_instruments(custom_df)
            st.session_state["custom_rows"] = custom_df.to_dict("records")
        up = sb.file_uploader(t("Your own NAV history (CSV)"), type=["csv"], key="nav_csv",
                              help=t("First column = date, then one column per fund, prices in the base currency. "
                                     "Semicolons and decimal commas are fine."))
        upload = up.getvalue() if up is not None else None
        base = sb.selectbox(t("Base currency"), ["EUR", "USD", "GBP", "CHF"], key="base",
                            help=t("Every price is converted to this currency with daily FX rates, so returns include "
                                   "the currency risk you actually bear."))

    with sb.expander(t("Period and data quality")):
        start = st.date_input(t("Start"), key="start")
        end = st.date_input(t("End"), key="end")
        backfill = st.checkbox(t("Backfill short fund histories with an ETF on the same index"), key="backfill",
                               disabled=demo)
        clean = st.checkbox(t("Remove one-day bad prints"), key="clean", disabled=demo)

    with sb.expander(t("Estimation")):
        freq = st.selectbox(t("Return frequency"), list(PERIODS_PER_YEAR), key="freq", format_func=t,
                            help=t("Weekly avoids the bias from exchanges closing at different times."))
        r_method = st.selectbox(t("Expected returns"), list(RETURN_METHODS), key="r_method",
                                format_func=lambda m: t(RETURN_METHODS[m]),
                                help=t("Long-term forecasts use forward-looking assumptions per asset class instead "
                                       "of extrapolating the past. Edit them in the Optimiser tab."))
        alpha = st.number_input(t("Expected alpha of active funds (annual %)"), -3.0, 3.0, step=0.25, key="alpha",
                                help=t("Extra return you expect from active managers before fees. The evidence "
                                       "(SPIVA) suggests about zero: most active funds trail their index by their "
                                       "fee difference.")) / 100
        c_method = st.selectbox(t("Covariance"), list(COV_METHODS), key="c_method",
                                format_func=lambda m: t(COV_METHODS[m]))
        rf = st.number_input(t("Risk-free rate (annual %)"), step=0.25, key="rf",
                             help=t("Average short-term rate: about 1-2% for EUR since 2015, 2% today.")) / 100

    with sb.expander(t("Constraints")):
        max_w = st.slider(t("Max weight per asset"), 0.05, 1.0, step=0.05, key="max_w",
                          help=t("Caps stop the optimiser from betting everything on one asset."))
        min_w = st.slider(t("Min weight per asset"), 0.0, 0.2, step=0.01, key="min_w")
        st.caption(t("Limits by asset class (look-through for mixed funds) and on active funds. They apply to "
                     "Max Sharpe, Min variance and Max diversification."))
        group_rows = list(ASSET_CLASSES) + ["Active funds"]
        group_df = st.data_editor(
            pd.DataFrame({"Group": [t(g) for g in group_rows], "Min %": 0.0, "Max %": 100.0}),
            hide_index=True, key="groups", disabled=["Group"],
            column_config={"Group": st.column_config.TextColumn(t("Group")),
                           "Min %": st.column_config.NumberColumn(min_value=0, max_value=100, step=5),
                           "Max %": st.column_config.NumberColumn(min_value=0, max_value=100, step=5)})
        group_df["Group"] = group_rows

    return dict(demo=demo, chosen=chosen, extra=extra, upload=upload, base=base, start=start, end=end,
                backfill=backfill, clean=clean, freq=freq, r_method=r_method, c_method=c_method, rf=rf,
                max_w=max_w, min_w=min_w, group_df=group_df, alpha=alpha, customs=customs)


# =========================================================================== load data
cfg = sidebar()
st.title("Portfolio Lab")

for inst in cfg["customs"]:
    register(inst)
custom_spec = json.dumps([{k: v for k, v in inst.__dict__.items() if k != "tags"} for inst in cfg["customs"]],
                         sort_keys=True, default=list)
ids = list(dict.fromkeys(cfg["chosen"] + cfg["extra"] + [i.symbol for i in cfg["customs"]]))
if not ids and not cfg["upload"]:
    st.info(t("Pick at least two assets in the sidebar to begin."))
    st.stop()

try:
    with st.spinner(t("Downloading prices and converting currencies...")):
        if cfg["demo"]:
            d = load_demo()
            data = PriceData(d.prices[ids], "EUR", {c: "EUR" for c in ids}, {c: c for c in ids})
        else:
            data = get_prices(tuple(ids), cfg["base"], cfg["backfill"], cfg["clean"], cfg["upload"], custom_spec)
except Exception as exc:
    st.error(t("Could not load prices: {err}").format(err=exc))
    st.caption(t("Tip: switch to the offline demo dataset, or check the ticker on finance.yahoo.com."))
    st.stop()

for w in data.warnings:
    st.warning(w)
prices_all = data.prices.loc[pd.Timestamp(cfg["start"]):pd.Timestamp(cfg["end"])]
if prices_all.shape[1] < 2 or len(prices_all) < 60:
    st.error(t("Need at least two assets with a common history of 60+ days in the chosen period."))
    st.stop()

base_meta = {c: describe(c) for c in prices_all.columns}
label = {c: base_meta[c].display for c in prices_all.columns}
prices = prices_all.rename(columns=label)
assets = list(prices.columns)
inv_label = {v: k for k, v in label.items()}
asset_colors = charts.color_map(assets)
ccy = data.base_currency
ppy = PERIODS_PER_YEAR[cfg["freq"]]
returns = to_returns(prices, cfg["freq"])


def data_status(asset: str) -> str:
    ident = inv_label[asset]
    if ident in data.synthetic:
        return t("Simulated from {p}").format(p=data.synthetic[ident])
    if ident in data.backfilled:
        return t("Real + backfilled with {p}").format(p=data.backfilled[ident])
    return t("Real")


# ---------------------------------------------------------------- instrument table (classification and TER editable)
tabs = st.tabs([t("Overview"), t("Optimiser"), t("My portfolio"), t("Savings plan"), t("Backtest"), t("Methodology")])
with tabs[0]:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(t("Assets"), len(assets))
    c2.metric(t("Period"), f"{prices.index[0]:%m/%Y} - {prices.index[-1]:%m/%Y}")
    c3.metric(t("Years of data"), f"{(prices.index[-1] - prices.index[0]).days / 365.25:.1f}")
    c4.metric(t("Return observations"), f"{len(returns)} {t(cfg['freq'])}")
    st.subheader(t("Instruments"))
    st.caption(t("Type, management, class, region and TER are editable: they drive the forecasts, the breakdowns "
                 "and the limits. TERs are indicative; check the KID."))
    inst_df = pd.DataFrame({
        "Asset": assets,
        "Name": [base_meta[inv_label[a]].name for a in assets],
        "Type": [t(base_meta[inv_label[a]].kind) for a in assets],
        "Management": [t(base_meta[inv_label[a]].management) for a in assets],
        "Class": [t(base_meta[inv_label[a]].asset_class) for a in assets],
        "Region": [t(base_meta[inv_label[a]].region) for a in assets],
        "TER %": [base_meta[inv_label[a]].ter * 100 for a in assets],
        "Data": [data_status(a) for a in assets],
        "Quote ccy": [data.currencies.get(inv_label[a], ccy) for a in assets],
    })
    inst_df = st.data_editor(
        inst_df, hide_index=True, key="inst", disabled=["Asset", "Name", "Data", "Quote ccy"],
        column_config={
            "Asset": st.column_config.TextColumn(t("Asset")), "Name": st.column_config.TextColumn(t("Name")),
            "Type": st.column_config.SelectboxColumn(t("Type"), options=[t(k) for k in KINDS]),
            "Management": st.column_config.SelectboxColumn(t("Management"), options=[t(m) for m in MANAGEMENT]),
            "Class": st.column_config.SelectboxColumn(t("Class"), options=[t(c) for c in ASSET_CLASSES + (MIXED,)]),
            "Region": st.column_config.SelectboxColumn(t("Region"), options=[t(r) for r in REGIONS]),
            "TER %": st.column_config.NumberColumn("TER %", format="%.2f", min_value=0.0, max_value=5.0, step=0.01),
            "Data": st.column_config.TextColumn(t("Data")), "Quote ccy": st.column_config.TextColumn(t("Quote ccy")),
        })


def edited_instrument(row) -> Instrument:
    base = base_meta[inv_label[row["Asset"]]]
    cls = i18n.untranslate(row["Class"])
    exposure = base.exposure if cls == base.asset_class else ()
    if cls == MIXED and not exposure:
        exposure = ((EQUITY, 0.5), (FIXED_INCOME, 0.5))
    return replace(base, kind=i18n.untranslate(row["Type"]), management=i18n.untranslate(row["Management"]),
                   asset_class=cls, region=i18n.untranslate(row["Region"]), ter=float(row["TER %"] or 0) / 100,
                   exposure=exposure)


meta = {row["Asset"]: edited_instrument(row) for _, row in inst_df.iterrows()}
ter = pd.Series({a: meta[a].ter for a in assets})

# ---------------------------------------------------------------- estimation
cov, hist_mu, est_info = get_estimates(returns, ppy, cfg["c_method"])
with tabs[1]:
    cma = dict(DEFAULT_CMA)
    if cfg["r_method"] == "long_term":
        with st.expander(t("Long-term assumptions by asset class (editable)")):
            st.caption(t("Nominal annual returns in EUR for the next 10-20 years, before fees. Defaults are round "
                         "numbers in the middle of the ranges published by large asset managers in 2025-2026. Each "
                         "asset gets the figure of its class and region, minus its TER (plus alpha for active "
                         "funds). Volatilities and correlations still come from the data."))
            cma_df = st.data_editor(
                pd.DataFrame({"Assumption": [t(k) for k in DEFAULT_CMA], "%": [v * 100 for v in DEFAULT_CMA.values()]}),
                hide_index=True, key="cma_edit", disabled=["Assumption"],
                column_config={"Assumption": st.column_config.TextColumn(t("Assumption")),
                               "%": st.column_config.NumberColumn("%", format="%.2f", step=0.25)})
            cma = {k: float(v) / 100 for k, v in zip(DEFAULT_CMA, cma_df["%"])}
    if cfg["r_method"] == "long_term":
        mu_est = long_term_returns(meta, ter, cma, cfg["alpha"]).reindex(assets)
    else:
        mu_est = hist_mu[cfg["r_method"]].copy()
        active = [a for a in assets if meta[a].management == "Active"]
        mu_est[active] += cfg["alpha"]
    with st.expander(t("Fine-tune the expected return of each asset")):
        st.caption(t("Compare the forecast with the past and type your own figure in the last column."))
        mu_df = st.data_editor(pd.DataFrame({
            "Asset": assets,
            "Forecast %": (mu_est.values * 100).round(2),
            "Historical %": (hist_mu["historical"].values * 100).round(2),
            "Std. error %": (est_info["se"].values * 100).round(2),
            "Use %": (mu_est.values * 100).round(2)}), hide_index=True, key="mu_edit",
            disabled=["Asset", "Forecast %", "Historical %", "Std. error %"],
            column_config={c: st.column_config.Column(t(c)) for c in
                           ("Asset", "Forecast %", "Historical %", "Std. error %", "Use %")})
mu = pd.Series(mu_df["Use %"].astype(float).values / 100, index=assets)

groups = []
for _, row in cfg["group_df"].iterrows():
    if row["Min %"] <= 0 and row["Max %"] >= 100:
        continue
    if row["Group"] == "Active funds":
        exposure = {a: 1.0 if meta[a].management == "Active" else 0.0 for a in assets}
    else:
        exposure = {a: meta[a].exposures.get(row["Group"], 0.0) for a in assets}
    members = [a for a, e in exposure.items() if e > 0]
    if members or row["Min %"] > 0:
        groups.append(GroupLimit(row["Group"], members, row["Min %"] / 100, row["Max %"] / 100, exposure))
max_w = max(cfg["max_w"], 1.0 / len(assets) + 1e-6)
spec = json.dumps({"lower": {a: cfg["min_w"] for a in assets}, "upper": {}, "default_upper": max_w,
                   "groups": [g.__dict__ for g in groups]})
if cfg["max_w"] < 1.0 / len(assets):
    st.info(t("Max weight raised to {w}: with {n} assets a lower cap cannot add up to 100%.").format(
        w=pct(max_w, 0), n=len(assets)))

try:
    portfolios, frontier = get_portfolios(mu, cov, cfg["rf"], spec)
except InfeasibleError as exc:
    st.error(t("Constraints are infeasible: {err}").format(err=exc))
    st.stop()

# ---------------------------------------------------------------- holdings (input lives in the My portfolio tab)
with tabs[2]:
    st.subheader(t("Your current positions"))
    st.caption(t("Enter the market value of each position (and what you paid, for the tax estimate). Leave zeros "
                 "for assets you do not own. Funds that are not in the list can be added from the sidebar."))
    seed = st.session_state.get("holdings_seed", {})
    hold_df = st.data_editor(
        pd.DataFrame({"Asset": assets,
                      "Value": [float(seed.get(a, {}).get("value", 0.0)) for a in assets],
                      "Cost basis": [float(seed.get(a, {}).get("cost", 0.0)) for a in assets]}),
        hide_index=True, key="holdings", disabled=["Asset"],
        column_config={"Asset": st.column_config.TextColumn(t("Asset")),
                       "Value": st.column_config.NumberColumn(t("Market value ({c})").format(c=ccy), min_value=0.0,
                                                              step=100.0, format="%.2f"),
                       "Cost basis": st.column_config.NumberColumn(t("Cost basis ({c})").format(c=ccy), min_value=0.0,
                                                                   step=100.0, format="%.2f")})
holdings = [Holding(a, float(v or 0.0), float(c or 0.0))
            for a, v, c in zip(hold_df["Asset"], hold_df["Value"], hold_df["Cost basis"])]
has_holdings = sum(h.value for h in holdings) > 0
opt_eval = PortfolioOptimizer(mu, cov, cfg["rf"])
if has_holdings:
    my_w = pd.Series({h.asset: h.value for h in holdings}).reindex(assets).fillna(0.0)
    portfolios = {**portfolios, "My portfolio": opt_eval.evaluate((my_w / my_w.sum()).values, "My portfolio")}


def render_breakdown(selection: dict[str, pd.Series], key: str) -> None:
    cols = st.columns(2)
    for i, dim in enumerate(DIMENSIONS):
        table = breakdown_table(selection, meta, dim)
        if table.empty:
            continue
        with cols[i % 2]:
            st.markdown(f"**{t(dim)}**" + (f" <span style='color:#898781'>({t('equity sleeve')})</span>"
                                            if dim == "Region" else ""), unsafe_allow_html=True)
            st.plotly_chart(charts.weights_bars(tr_index(table), charts.color_map(list(selection)), height=220),
                            width="stretch", key=f"bd_{key}_{dim}")


# =========================================================================== Overview tab
with tabs[0]:
    stats = M.summary_table(prices.pct_change().dropna(), 252, cfg["rf"])
    stats.insert(0, "TER", ter)
    st.subheader(t("Historical performance (daily data, in {c})").format(c=ccy))
    if data.synthetic:
        st.caption(t("Simulated funds show their proxy's history minus fees, not the fund's own record."))
    fmt = {c: "{:.2%}" for c in stats.columns}
    fmt.update({"Sharpe": "{:.2f}", "Sortino": "{:.2f}", "Calmar": "{:.2f}", "Longest drawdown (days)": "{:.0f}"})
    st.dataframe(styled(tr_columns(stats), {t(k): v for k, v in fmt.items()}), width="stretch")
    log = st.toggle(t("Log scale"), value=True, key="log_overview")
    st.plotly_chart(charts.growth_chart(prices / prices.iloc[0] * 100, asset_colors, log, t("Growth of 100")),
                    width="stretch")
    st.plotly_chart(charts.drawdown_chart(prices, asset_colors), width="stretch")
    a, b = st.columns(2)
    with a:
        st.subheader(t("Correlation"))
        st.plotly_chart(charts.correlation_heatmap(estimators.cov_to_corr(cov)), width="stretch")
    with b:
        st.subheader(t("Calendar-year returns"))
        st.plotly_chart(charts.calendar_heatmap(M.calendar_year_returns(prices)), width="stretch")
    notes = [f"**{a_}**: {t(meta[a_].note)}" for a_ in assets if meta[a_].note]
    if notes:
        with st.expander(t("Notes on the instruments")):
            st.markdown("\n\n".join(notes))

# =========================================================================== Optimiser tab
with tabs[1]:
    info = []
    if cfg["r_method"] == "long_term":
        info.append(t("Expected returns: long-term forecasts net of TER."))
    elif cfg["r_method"] == "bayes_stein":
        info.append(t("Bayes-Stein pulled the means {p} of the way towards the common mean.").format(
            p=pct(est_info["phi"], 0)))
    if est_info["delta"] is not None:
        info.append(t("Ledoit-Wolf shrinkage intensity: {p}.").format(p=pct(est_info["delta"], 0)))
    st.caption(" ".join(info))

    c1, c2 = st.columns([3, 1])
    with c2:
        st.markdown(f"**{t('Build your own point on the frontier')}**")
        gmv_vol = portfolios["Minimum variance"].volatility
        top_vol = max(p.volatility for p in frontier)
        lo_v, hi_v = float(np.ceil(gmv_vol * 1000) / 1000), float(np.floor(top_vol * 1000) / 1000)
        hi_v = max(hi_v, lo_v + 0.001)
        target_vol = st.slider(t("Target volatility"), lo_v, hi_v, float(round((lo_v + hi_v) / 2, 3)), 0.001,
                               format="%.3f")
        try:
            custom = PortfolioOptimizer(mu, cov, cfg["rf"], _constraints_from_json(spec)).efficient_risk(target_vol)
            custom.name = "Target volatility"
            st.metric(t("Expected return"), pct(custom.expected_return))
            st.metric("Sharpe", f"{custom.sharpe:.2f}")
        except (InfeasibleError, RuntimeError) as exc:
            custom = None
            st.warning(str(exc))
        show_cloud = st.toggle(t("Show random portfolios"), value=True, key="cloud")
    shown = dict(portfolios)
    if custom is not None:
        shown["Target volatility"] = custom
    with c1:
        st.plotly_chart(charts.efficient_frontier(
            frontier, shown, mu, pd.Series(np.sqrt(np.diag(cov.values)), index=assets), cfg["rf"],
            get_cloud(mu, cov) if show_cloud else None, asset_colors), width="stretch")

    rows = []
    for name, p in shown.items():
        active_share = float(sum(p.weights[a] for a in assets if meta[a].management == "Active"))
        rows.append({"Portfolio": t(name), "Expected return": p.expected_return, "Volatility": p.volatility,
                     "Sharpe": p.sharpe, "TER": float(p.weights @ ter), "Active funds": active_share,
                     "Effective N": effective_n(p.weights),
                     "Diversification ratio": diversification_ratio(p.weights, cov),
                     "Largest weight": float(p.weights.max()),
                     "Honours constraints": t("yes") if name in CONSTRAINED | {"Target volatility"} else t("no")})
    table = pd.DataFrame(rows).set_index("Portfolio")
    st.subheader(t("Strategy comparison"))
    fmt = {"Expected return": "{:.2%}", "Volatility": "{:.2%}", "Sharpe": "{:.2f}", "TER": "{:.2%}",
           "Active funds": "{:.0%}", "Effective N": "{:.1f}", "Diversification ratio": "{:.2f}",
           "Largest weight": "{:.1%}"}
    st.dataframe(styled(tr_columns(table), {t(k): v for k, v in fmt.items()}), width="stretch")
    st.caption(t("Expected return and volatility are forward-looking estimates. The Backtest tab shows how each "
                 "strategy really behaved, out of sample."))

    st.subheader(t("Weights and breakdown"))
    pick = st.multiselect(t("Portfolios"), list(shown), format_func=t,
                          default=[n for n in ("Maximum Sharpe", "Risk parity", "My portfolio") if n in shown],
                          key=f"w_pick_{len(shown)}")
    if pick:
        wdf = pd.DataFrame({n: shown[n].weights for n in pick})
        st.plotly_chart(charts.weights_bars(wdf, charts.color_map(list(shown))), width="stretch")
        render_breakdown({n: shown[n].weights for n in pick}, "opt")
        st.download_button(t("Download weights (CSV)"), tr_columns(wdf).to_csv().encode(), "weights.csv", "text/csv")

    st.subheader(t("Where does the risk come from?"))
    focus = st.selectbox(t("Portfolio"), list(shown), format_func=t, key=f"rc_pick_{len(shown)}")
    rc = risk_contributions(shown[focus].weights, cov)
    st.plotly_chart(charts.risk_vs_weight(shown[focus].weights, rc), width="stretch")
    st.caption(t("Risk contribution = share of portfolio variance coming from each asset. In a typical 60/40 "
                 "portfolio equities bring around 90% of the risk."))

# =========================================================================== My portfolio tab
with tabs[2]:
    if not has_holdings:
        st.info(t("Enter your positions above to compare them with the optimised portfolios and plan a rebalance."))
    else:
        me = portfolios["My portfolio"]
        total = sum(h.value for h in holdings)
        cost_total = sum(h.cost_basis for h in holdings)
        k = st.columns(5)
        k[0].metric(t("Portfolio value"), money(total, ccy))
        k[1].metric(t("Unrealised gain"), money(total - cost_total, ccy) if cost_total else "n/a",
                    pct(total / cost_total - 1) if cost_total else None)
        k[2].metric(t("Expected return"), pct(me.expected_return))
        k[3].metric(t("Volatility"), pct(me.volatility))
        k[4].metric(t("Annual cost (TER)"), f"{money(float(me.weights @ ter) * total, ccy)} "
                                            f"({pct(float(me.weights @ ter), 2)})")
        try:
            same_risk = PortfolioOptimizer(mu, cov, cfg["rf"], _constraints_from_json(spec)).efficient_risk(
                me.volatility)
            gain = same_risk.expected_return - me.expected_return
            if gain > 0.0005:
                st.markdown(t("With the same volatility ({v}), the efficient portfolio would expect **{r}** a year, "
                              "{g} more than yours (about {m} a year on your current balance).").format(
                    v=pct(me.volatility), r=pct(same_risk.expected_return), g=pct(gain, 2), m=money(gain * total, ccy)))
            else:
                st.success(t("Your portfolio is already on (or very close to) the efficient frontier."))
        except (InfeasibleError, RuntimeError):
            pass

        st.subheader(t("Rebalancing plan"))
        c1, c2, c3 = st.columns(3)
        target_name = c1.selectbox(t("Target portfolio"), [n for n in shown if n != "My portfolio"], format_func=t,
                                   key="target_pick")
        new_cash = c2.number_input(t("New money to invest ({c})").format(c=ccy), value=1000.0, step=100.0,
                                   key="new_cash")
        sells = c3.toggle(t("Allow selling (full rebalance)"), value=False, key="sells",
                          help=t("Off: only the new money is used, nothing is sold and no tax is triggered."))
        target_w = shown[target_name].weights
        try:
            plan = rebalance_plan(holdings, target_w, new_cash, allow_sells=sells,
                                  is_fund={a: meta[a].is_fund for a in assets})
        except ValueError as exc:
            st.error(str(exc))
            plan = None
        if plan is not None:
            plan_show = plan.copy()
            plan_show["Traspaso eligible"] = plan_show["Traspaso eligible"].map({True: t("yes"), False: t("no")})
            fmt = {"Current value": "{:,.2f}", "Trade": "{:+,.2f}", "Value after": "{:,.2f}", "Realised gain": "{:,.2f}",
                   "Estimated tax": "{:,.2f}", "Current weight": "{:.1%}", "Target weight": "{:.1%}",
                   "Weight after": "{:.1%}"}
            st.dataframe(styled(tr_columns(plan_show), {t(k_): v for k_, v in fmt.items()}), width="stretch")
            k = st.columns(3)
            k[0].metric(t("Distance to target before"), pct(tracking_gap(me.weights, target_w)))
            k[1].metric(t("Distance to target after"), pct(tracking_gap(plan["Weight after"], target_w)))
            k[2].metric(t("Estimated Spanish tax (IRPF)"), money(plan["Estimated tax"].sum(), ccy))
            st.caption(t("Tax: savings-base brackets 19% to 30% on realised gains, average-cost method, no loss "
                         "offsetting. Fund sales are assumed to go by traspaso (tax-deferred). Order of magnitude "
                         "only, not tax advice."))
        st.subheader(t("Your allocation vs the target"))
        render_breakdown({"My portfolio": me.weights, target_name: target_w}, "mine")

    st.divider()
    st.subheader(t("Save this session"))
    st.caption(t("Downloads your universe, settings, own funds and holdings so you can load them next time."))
    widget_keys = [k_ for k_ in DEFAULTS if k_ not in ("start", "end")] + ["demo_assets"]
    payload = {"widgets": {k_: st.session_state[k_] for k_ in widget_keys if k_ in st.session_state},
               "custom_funds": st.session_state.get("custom_rows", []),
               "holdings": {h.asset: {"value": h.value, "cost": h.cost_basis}
                            for h in holdings if h.value or h.cost_basis}}
    st.download_button(t("Download session (.json)"), json.dumps(payload, indent=2, default=str).encode(),
                       "portfolio_session.json", "application/json")

# =========================================================================== Savings plan tab
with tabs[3]:
    st.caption(t("Project a portfolio with monthly contributions. The expected path uses the long-term return; the "
                 "Monte Carlo shows the range of outcomes around it."))
    options = list(shown)
    default_idx = options.index("My portfolio") if "My portfolio" in options else 0
    c = st.columns(4)
    mc_name = c[0].selectbox(t("Portfolio"), options, index=default_idx, format_func=t, key=f"mc_pick_{len(options)}")
    p = shown[mc_name]
    start_val = float(sum(h.value for h in holdings)) if has_holdings else 10_000.0
    initial = c[1].number_input(t("Initial capital ({c})").format(c=ccy), 0.0, 1e9, start_val, 1000.0,
                                key=f"mc_init_{start_val:.0f}")
    monthly = c[2].number_input(t("Monthly contribution ({c})").format(c=ccy), -1e6, 1e6, 300.0, 50.0, key="mc_month",
                                help=t("Negative = monthly withdrawal (retirement phase)."))
    years = c[3].slider(t("Horizon (years)"), 1, 50, 25, key="mc_years")
    c = st.columns(4)
    exp_r = c[0].number_input(t("Expected return (annual %, net of TER)"), -20.0, 40.0,
                              round(p.expected_return * 100, 2), 0.25) / 100
    vol = c[1].number_input(t("Volatility (annual %)"), 0.0, 100.0, round(p.volatility * 100, 2), 0.25) / 100
    fee = c[2].number_input(t("Other annual costs (%)"), 0.0, 5.0, 0.0, 0.05, key="mc_fee",
                            help=t("Platform or custody fees. Fund TERs are already inside the expected return.")) / 100
    infl = c[3].number_input(t("Inflation (annual %)"), -2.0, 15.0, 2.0, 0.25, key="mc_infl") / 100
    if exp_r > 0.08:
        st.caption(t("Heads-up: {r} a year is above the long-run nominal return of global equities (roughly 6-8%).")
                   .format(r=pct(exp_r)))
    c = st.columns(4)
    growth = c[0].number_input(t("Contribution growth (annual %)"), 0.0, 20.0, 0.0, 0.5, key="mc_growth") / 100
    goal = c[1].number_input(t("Goal in today's money ({c}, 0 = none)").format(c=ccy), 0.0, 1e10, 0.0, 10_000.0,
                             key="mc_goal")
    method = c[2].selectbox(t("Return model"), METHODS, key="mc_method",
                            format_func=lambda m: t({"lognormal": "Log-normal", "student_t": "Student-t (fat tails)",
                                                     "bootstrap": "Historical block bootstrap"}[m]))
    n_sims = c[3].select_slider(t("Simulations"), [1000, 2000, 5000, 10000, 20000], value=5000, key="mc_n")
    real = st.toggle(t("Show in today's money (inflation-adjusted)"), value=True, key="mc_real")

    st.subheader(t("Expected path"))
    proj = projection_table(initial, monthly, years, exp_r - fee, growth, infl)
    k = st.columns(4)
    k[0].metric(t("Value at the end"), money(proj["Value"].iloc[-1], ccy))
    k[1].metric(t("Value in today's money"), money(proj["Value (today's money)"].iloc[-1], ccy),
                help=t("What the final amount would buy today, after {i} inflation a year.").format(i=pct(infl)))
    k[2].metric(t("Money contributed"), money(proj["Contributed"].iloc[-1], ccy))
    k[3].metric(t("Investment gains"), money(proj["Value"].iloc[-1] - proj["Contributed"].iloc[-1], ccy),
                pct(proj["Value"].iloc[-1] / max(proj["Contributed"].iloc[-1], 1) - 1, 0) + " " + t("over contributions"),
                delta_color="off")
    a, b = st.columns([3, 2])
    with a:
        st.plotly_chart(charts.projection_chart(proj, real), width="stretch")
    with b:
        marks = sorted({y for y in (1, 3, 5, 10, 15, 20, 25, 30, 40, 50) if y <= years} | {years})
        shown_tab = proj.loc[marks, ["Contributed", "Value", "Gains", "Value (today's money)"]]
        shown_tab = shown_tab.rename(index=lambda y: f"{t('Year')} {y}")
        shown_tab.index.name = None
        st.dataframe(styled(tr_columns(shown_tab), "{:,.0f}"), width="stretch")

    st.subheader("Monte Carlo")
    monthly_hist = to_returns(prices, "monthly") @ p.weights.reindex(assets).fillna(0).values
    inp = SimulationInput(initial=initial, monthly_contribution=monthly, contribution_growth=growth, years=years,
                          expected_return=exp_r, volatility=vol, annual_fee=fee, inflation=infl, method=method,
                          n_sims=int(n_sims), target=goal or None)
    try:
        sim = simulate(inp, history=monthly_hist)
    except ValueError as exc:
        st.error(str(exc))
        sim = None
    if sim is not None:
        summ = sim.summary()
        k = st.columns(5)
        k[0].metric(t("Median outcome"), money(float(np.median(sim.final(real))), ccy))
        k[1].metric(t("Bad case (P5)"), money(float(np.percentile(sim.final(real), 5)), ccy))
        k[2].metric(t("Good case (P95)"), money(float(np.percentile(sim.final(real), 95)), ccy))
        k[3].metric(t("Median worst drawdown"), pct(summ["Median worst drawdown"]))
        if goal:
            k[4].metric(t("Chance of reaching the goal"), pct(summ["Probability of reaching the goal"], 0))
        elif monthly < 0:
            k[4].metric(t("Chance of running out"), pct(summ["Probability of ruin"], 0))
        else:
            k[4].metric(t("Chance of ending below contributions"), pct(summ["Probability of ending below contributions"], 0))
        pct_df = sim.percentiles(real)
        contributed = sim.contributed / (sim.deflator if real else 1.0)
        rng = np.random.default_rng(0)
        sample = sim.paths[rng.choice(len(sim.paths), size=min(30, len(sim.paths)), replace=False)]
        if real:
            sample = sample / sim.deflator
        st.plotly_chart(charts.fan_chart(pct_df, contributed, goal or None, sample), width="stretch")
        st.plotly_chart(charts.final_histogram(sim.final(real), float(contributed[-1]), goal or None), width="stretch")
        if goal and st.button(t("How much should I contribute each month to reach the goal?"), key="solve"):
            with st.spinner(t("Solving...")):
                res = {conf: required_contribution(inp, goal, conf, monthly_hist) for conf in (0.5, 0.75, 0.9)}
            st.table(pd.DataFrame({t("Probability of success"): ["50%", "75%", "90%"],
                                   t("Monthly contribution ({c})").format(c=ccy): [money(v, ccy) for v in res.values()]}))

# =========================================================================== Backtest tab
with tabs[4]:
    st.caption(t("Walk-forward: at every rebalance date each strategy is re-optimised using only the past "
                 "lookback years, then held until the next date. Prices are already net of each fund's TER; "
                 "trading costs are deducted on every rebalance."))
    c = st.columns(4)
    lookback = c[0].slider(t("Lookback (years)"), 1.0, 5.0, 3.0, 0.5, key="lookback")
    rebalance = c[1].selectbox(t("Rebalance"), [r for r in REBALANCE_RULES if r != "Never"], index=1, key="rebal",
                               format_func=t)
    cost_bps = c[2].number_input(t("Trading cost (bps)"), 0.0, 100.0, 10.0, 1.0, key="cost_bps")
    bench = c[3].selectbox(t("Benchmark"), assets, index=0, key="bench")
    pool = list(STRATEGIES) + (["My portfolio"] if has_holdings else [])
    chosen_bt = st.multiselect(t("Strategies"), pool, format_func=t, key=f"bt_pick_{has_holdings}",
                               default=["Maximum Sharpe", "Risk parity", "Equal weight"] +
                               (["My portfolio"] if has_holdings else []))
    if cfg["r_method"] == "long_term":
        st.caption(t("Long-term forecasts are not available point-in-time, so the walk-forward uses Bayes-Stein "
                     "estimates from each past window."))
    bt_start = lookback_start(prices, lookback)
    if bt_start >= prices.index[-1] - pd.Timedelta(days=365):
        st.warning(t("Not enough history for this lookback. Shorten it or pick assets with longer histories."))
    elif chosen_bt:
        results = {}
        with st.spinner(t("Running walk-forward backtests...")):
            for name in chosen_bt:
                kind = "static" if name in ("My portfolio", "Equal weight") else "dynamic"
                w = portfolios[name].weights if kind == "static" else None
                results[name] = get_backtest(prices, kind, name, w, rebalance, bt_start, cost_bps, lookback,
                                             cfg["freq"], cfg["r_method"], cfg["c_method"], cfg["rf"], spec)
            bench_name = f"{bench} ({t('buy and hold')})"
            bench_w = pd.Series(0.0, index=assets)
            bench_w[bench] = 1.0
            results[bench_name] = get_backtest(prices, "static", bench_name, bench_w, "Never", bt_start, cost_bps,
                                               lookback, cfg["freq"], cfg["r_method"], cfg["c_method"], cfg["rf"], spec)
        wealth = pd.DataFrame({n: r.wealth for n, r in results.items()})
        colors = charts.color_map(list(wealth.columns))
        st.plotly_chart(charts.growth_chart(wealth * 100, colors, False, t("Growth of 100, out-of-sample")),
                        width="stretch")
        st.plotly_chart(charts.drawdown_chart(wealth, colors), width="stretch")
        bench_r = wealth[bench_name].pct_change().dropna()
        rows = {}
        for n in wealth.columns:
            s = M.summary(wealth[n].pct_change().dropna(), 252, cfg["rf"], bench_r)
            s["Avg turnover / rebalance"] = (float(results[n].turnover.iloc[1:].mean())
                                            if len(results[n].turnover) > 1 else 0.0)
            rows[t(n)] = s
        bt_table = pd.DataFrame(rows).T
        fmt = {c_: "{:.2%}" for c_ in bt_table.columns}
        fmt.update({k_: "{:.2f}" for k_ in ("Sharpe", "Sortino", "Calmar", "Beta", "Correlation", "Information ratio")})
        fmt["Longest drawdown (days)"] = "{:.0f}"
        st.dataframe(styled(tr_columns(bt_table), {t(k_): v for k_, v in fmt.items()}, na_rep="-"),
                     width="stretch")

        st.subheader(t("Investing every month over this period"))
        c = st.columns(2)
        dca_m = c[0].number_input(t("Monthly contribution ({c})").format(c=ccy), 0.0, 1e6, 300.0, 50.0, key="dca_m")
        dca_0 = c[1].number_input(t("Initial capital ({c})").format(c=ccy), 0.0, 1e9, 0.0, 1000.0, key="dca_0")
        paths, dca_rows = {}, {}
        for n in wealth.columns:
            path, irr = historical_dca(wealth[n], dca_m, dca_0)
            paths[n] = path
            dca_rows[t(n)] = {"Contributed": path["Contributed"].iloc[-1], "Final value": path["Value"].iloc[-1],
                              "Gains": path["Value"].iloc[-1] - path["Contributed"].iloc[-1],
                              "Money-weighted return (IRR)": irr}
        st.plotly_chart(charts.dca_chart(paths, colors), width="stretch")
        dca_tab = pd.DataFrame(dca_rows).T
        st.dataframe(styled(tr_columns(dca_tab), {t("Contributed"): "{:,.0f}", t("Final value"): "{:,.0f}",
                                                       t("Gains"): "{:,.0f}",
                                                       t("Money-weighted return (IRR)"): "{:.2%}"}), width="stretch")
        st.caption(t("The money-weighted return (IRR / TIR) accounts for when each contribution was made, so it is "
                     "the return you would actually have earned."))
        dyn = [n for n in chosen_bt if n not in ("My portfolio", "Equal weight")]
        if dyn:
            which = st.selectbox(t("Weights over time"), dyn, format_func=t, key="wot")
            st.plotly_chart(charts.weights_over_time(results[which].weights, asset_colors), width="stretch")

# =========================================================================== Methodology tab
with tabs[5]:
    st.markdown(i18n.METHODOLOGY[lang])
