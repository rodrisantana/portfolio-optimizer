"""Portfolio Lab: optimise, backtest and plan a portfolio of ETFs, ETCs, index funds and active funds.

Run with:  streamlit run app.py          (add ?lang=en to the URL for English)
"""

from __future__ import annotations

import base64
import json
from dataclasses import replace
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from portfolio_optimizer import charts, estimators, i18n
from portfolio_optimizer import metrics as M
from portfolio_optimizer.assumptions import (
    DEFAULT_CMA,
    DEFAULT_PRESET,
    JPM_EUR_INFLATION,
    long_term_returns,
    median_growth,
    preset_table,
)
from portfolio_optimizer.assumptions import PRESETS as CMA_PRESETS
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
    find,
    is_isin,
    parse_proxy,
    register,
)
from portfolio_optimizer.data import (
    PERIODS_PER_YEAR,
    PriceData,
    account_series,
    load_demo,
    load_prices,
    parse_uploaded_csv,
    to_returns,
)
from portfolio_optimizer.holdings import Holding, rebalance_plan, tracking_gap
from portfolio_optimizer.montecarlo import METHODS, SimulationInput, horizon_table, required_contribution, simulate
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
from portfolio_optimizer.portfolio_io import TEMPLATE, account_instrument, export_portfolio, parse_portfolio, to_excel_bytes
from portfolio_optimizer.search import instrument_from_dict, instrument_to_dict, search_instruments

APP_NAME = "Portfolio Lab"          # one place to rename the product
ASSETS = Path(__file__).resolve().parent / "assets"
LOGO = str(ASSETS / "logo-mark.svg")
REPO_URL = "https://github.com/rodrisantana/portfolio-optimizer"
JPM_URL = ("https://am.jpmorgan.com/content/dam/jpm-am-aem/global/en/insights/portfolio-insights/ltcma/noindex/"
           "ltcma-2027-report.pdf")

st.set_page_config(page_title=APP_NAME, page_icon=str(ASSETS / "logo-mark-64.png"), layout="wide",
                   initial_sidebar_state="expanded")
st.logo(LOGO, icon_image=LOGO, size="large")

st.markdown("""
<style>
.block-container {padding-top: 3.2rem; max-width: 1380px;}
/* metric tiles as cards */
[data-testid="stMetric"] {border: 1px solid rgba(120,140,170,0.22); border-radius: 14px; padding: 14px 16px;
  background: color-mix(in srgb, currentColor 2%, transparent); box-shadow: 0 1px 2px rgba(15,27,45,0.04);}
[data-testid="stMetricLabel"] p {font-size: 0.78rem; letter-spacing: 0.04em; text-transform: uppercase; opacity: 0.7;}
/* tabs as a segmented control (no underline) */
.stTabs [role="tablist"] {gap: 4px; flex-wrap: wrap; border: 1px solid rgba(120,140,170,0.25); border-radius: 14px;
  padding: 4px; width: fit-content; max-width: 100%; background: color-mix(in srgb, currentColor 3%, transparent);
  box-shadow: none !important;}
.stTabs [role="tablist"]::before, .stTabs [role="tablist"]::after,
.stTabs [data-testid="stTab"]::before, .stTabs [data-testid="stTab"]::after {display: none !important; content: none !important;}
.stTabs [data-testid="stTab"] {height: 38px; padding: 0 16px; border-radius: 10px; border: none !important;
  box-shadow: none !important; display: flex; align-items: center;}
.stTabs [data-testid="stTab"] p {font-weight: 600; font-size: 0.92rem; opacity: 0.75;}
.stTabs [data-testid="stTab"]:hover p {opacity: 1;}
.stTabs [data-testid="stTab"][aria-selected="true"] {background: #FFFFFF; box-shadow: 0 1px 3px rgba(15,27,45,0.18) !important;}
.stTabs [data-testid="stTab"][aria-selected="true"] p {color: #0B1C33 !important; opacity: 1;}
.stTabs [role="tablist"] > div:not([data-testid="stTab"]) {display: none !important;}
.stTabs .react-aria-SelectionIndicator {display: none !important;}
[data-testid="stTabPanel"] {padding-top: 14px;}
/* sidebar sections */
.pl-sec {font-size: 0.7rem; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; opacity: 0.55;
  margin: 18px 0 2px 0;}
/* navbar */
.pl-brand {display: flex; align-items: center; gap: 12px;}
.pl-brand img {width: 40px; height: 40px;}
.pl-brand .n {font-size: 1.35rem; font-weight: 800; letter-spacing: -0.02em; line-height: 1;}
.pl-brand .s {font-size: 0.8rem; opacity: 0.6; margin-top: 3px;}
/* market ticker */
.pl-ticker {display: flex; gap: 26px; overflow-x: auto; white-space: nowrap; padding: 10px 2px 12px 2px;
  border-bottom: 1px solid rgba(120,140,170,0.2); margin-bottom: 18px; font-size: 0.85rem; scrollbar-width: none;}
.pl-ticker span.n {opacity: 0.7; margin-right: 6px;}
.pl-ticker b {font-variant-numeric: tabular-nums; margin-right: 6px; font-weight: 700;}
/* landing cards */
.pl-tile {border: 1px solid rgba(120,140,170,0.25); border-radius: 16px; padding: 18px 18px 6px 18px; height: 100%;
  background: color-mix(in srgb, currentColor 2%, transparent);}
.pl-tile .ic {width: 38px; height: 38px; border-radius: 11px; display: grid; place-items: center; font-weight: 800;
  color: #fff; margin-bottom: 10px;}
.pl-tile h4 {margin: 0 0 4px 0; font-size: 1.05rem;}
.pl-tile p {opacity: 0.75; font-size: 0.9rem;}
/* footer */
.pl-foot {margin-top: 48px; padding: 26px 0 8px 0; border-top: 1px solid rgba(120,140,170,0.25); font-size: 0.85rem;
  display: grid; grid-template-columns: 2fr 1fr 1fr 1fr; gap: 22px;}
.pl-foot .h {font-size: 0.72rem; letter-spacing: 0.12em; text-transform: uppercase; opacity: 0.55; margin: 0 0 8px 0;}
.pl-foot a {display: block; text-decoration: none; opacity: 0.85; margin-bottom: 4px;}
.pl-foot .d {opacity: 0.65; line-height: 1.5;}
@media (max-width: 800px) {.pl-foot {grid-template-columns: 1fr 1fr;}}
h2, h3 {letter-spacing: -0.01em;}
/* hero */
.pl-hero {border-radius: 20px; padding: 24px 28px; margin-bottom: 18px; color: #fff;
  background: radial-gradient(120% 140% at 100% 0%, #13a594 0%, #0e6f78 32%, #0b1c33 75%);
  display: flex; flex-wrap: wrap; gap: 18px 40px; align-items: flex-end; justify-content: space-between;}
.pl-hero h1 {font-size: 2.1rem; font-weight: 800; margin: 0; color: #fff; letter-spacing: -0.02em; padding: 0;}
.pl-hero .tag {opacity: 0.85; margin-top: 4px; max-width: 46ch; font-size: 0.98rem;}
.pl-hero .kpis {display: flex; gap: 28px; flex-wrap: wrap;}
.pl-hero .kpi .l {font-size: 0.72rem; letter-spacing: 0.08em; text-transform: uppercase; opacity: 0.75;}
.pl-hero .kpi .v {font-size: 1.55rem; font-weight: 800; font-variant-numeric: tabular-nums;}
.pl-hero .chip {display: inline-block; font-size: 0.75rem; padding: 3px 10px; border-radius: 999px;
  background: rgba(255,255,255,0.14); margin: 8px 6px 0 0;}
.pos {color: #0E9F6E;} .neg {color: #D64545;}
.pl-hero .pos {color: #7CF0C5;} .pl-hero .neg {color: #FFB4B4;}
/* empty state */
.pl-empty {border: 1.5px dashed rgba(14,143,130,0.45); border-radius: 18px; padding: 28px; text-align: left;
  background: color-mix(in srgb, #0E8F82 5%, transparent);}
.pl-empty h3 {margin-top: 0;}
.pl-card {border: 1px solid rgba(120,140,170,0.22); border-radius: 14px; padding: 14px 16px; margin-bottom: 8px;}
.pl-badge {display: inline-block; font-size: 0.72rem; font-weight: 600; padding: 2px 8px; border-radius: 999px;
  background: rgba(14,143,130,0.12); color: #0E8F82; margin-left: 6px;}
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------------- language
qp_lang = st.query_params.get("lang")
if "_lang_next" in st.session_state:                   # a loaded session asks for its language
    st.session_state["lang"] = st.session_state.pop("_lang_next")
st.session_state.setdefault("lang", qp_lang if qp_lang in ("es", "en") else "es")
_logo_b64 = base64.b64encode(Path(LOGO).read_bytes()).decode()
nav_l, nav_r = st.columns([5, 1], vertical_alignment="center")
with nav_r:
    lang = st.segmented_control("lang", ["es", "en"], key="lang", required=True, label_visibility="collapsed",
                                format_func={"es": "ES", "en": "EN"}.get, width="stretch")
if st.query_params.get("lang") != lang:
    st.query_params["lang"] = lang
i18n.set_language(lang)
t = i18n.t
charts.set_translator(t)
nav_l.markdown(f"<div class='pl-brand'><img src='data:image/svg+xml;base64,{_logo_b64}'/><div><div class='n'>"
               f"{APP_NAME}</div><div class='s'>{t('Build, compare and plan your investment portfolio')}</div></div>"
               f"</div>", unsafe_allow_html=True)

# Widgets whose option labels are translated keep one state per language plus a stable "mirror" value,
# so switching language never feeds a translated label back as a value.
LANG_WIDGETS = ("source", "preset", "catalog_assets", "freq", "r_method", "c_method", "cma_preset", "rebal",
                "mc_method", "target_pick", "dlg_mode", "dlg_kind", "wot", "search_pick", "dlg_pick", "dlg_sym")


for _name in LANG_WIDGETS:                     # mirror the last value of every language-aware widget
    for _l in (st.session_state.get("_lang_last"), lang):
        if _l and f"{_name}__{_l}" in st.session_state:
            st.session_state[_name] = st.session_state[f"{_name}__{_l}"]
st.session_state["_lang_last"] = lang


def lkey(name: str) -> str:
    k_ = f"{name}__{lang}"
    if k_ not in st.session_state and name in st.session_state:
        st.session_state[k_] = st.session_state[name]
    return k_


def set_state(name: str, value) -> None:
    """Change a language-aware widget's value from code (before or after it is drawn)."""
    st.session_state[name] = value
    for l_ in ("es", "en"):
        st.session_state.pop(f"{name}__{l_}", None)


@st.cache_data(ttl=1800, show_spinner=False)
def market_snapshot() -> list[tuple[str, float, float]]:
    """Last close and daily change of a few reference markets, for the ticker strip."""
    import yfinance as yf
    out = []
    for sym_, name_ in (("^GSPC", "S&P 500"), ("^STOXX50E", "Euro Stoxx 50"), ("^IBEX", "IBEX 35"),
                        ("EUNL.DE", "MSCI World"), ("^N225", "Nikkei 225"), ("GC=F", "Oro / Gold"),
                        ("EURUSD=X", "EUR/USD"), ("BTC-EUR", "Bitcoin")):
        try:
            h = yf.Ticker(sym_).history(period="7d", auto_adjust=True)["Close"].dropna()
            if len(h) >= 2:
                out.append((name_, float(h.iloc[-1]), float(h.iloc[-1] / h.iloc[-2] - 1)))
        except Exception:
            continue
    return out

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
    for spec in json.loads(custom_spec):                 # make user instruments known inside the cached call too
        register(instrument_from_dict(spec))
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
    "catalog_assets": [], "extra": "", "base": "EUR",
    "start": date(2015, 1, 1), "end": date.today(), "backfill": True, "clean": True,
    "freq": "weekly", "r_method": "long_term", "c_method": "ledoit_wolf", "rf": 2.6, "max_w": 0.5, "min_w": 0.0,
    "alpha": 0.0, "cma_preset": DEFAULT_PRESET,
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


CATALOG_SYMBOLS = {i.symbol for i in CATALOG}
ACCOUNT_COLUMNS = ["Name", "TAE %", "Type"]


def current_portfolio() -> dict[str, dict]:
    """Positions as {symbol: {"value": €, "cost": €}}, including edits made in the positions table."""
    return dict(st.session_state.get("_pf_effective", st.session_state.get("portfolio", {})))


def save_portfolio(pf: dict[str, dict]) -> None:
    st.session_state["portfolio"] = pf
    st.session_state["_pf_effective"] = pf
    st.session_state.pop("pf_ed", None)          # rebuild the positions editor from the new state


def add_to_portfolio(inst: Instrument, value: float, cost: float) -> None:
    pf = current_portfolio()
    if inst.rate is not None:
        rows = [r for r in st.session_state.get("accounts_seed", []) if r.get("Name") != inst.symbol]
        rows.append({"Name": inst.symbol, "TAE %": round(inst.rate * 100, 3), "Type": t(inst.kind)})
        st.session_state["accounts_seed"] = rows
        st.session_state.pop("accounts_ed", None)
    elif inst.symbol not in CATALOG_SYMBOLS:
        st.session_state.setdefault("added", {})[inst.symbol] = instrument_to_dict(inst)
    prev = pf.get(inst.symbol, {"value": 0.0, "cost": 0.0})
    pf[inst.symbol] = {"value": prev["value"] + value, "cost": prev["cost"] + (cost or 0.0)}
    save_portfolio(pf)
    st.session_state["_import_msg"] = t("Added to your portfolio: {n}").format(n=inst.display)


SAMPLE_PORTFOLIO = {"EUNL.DE": (9200, 7000), "IE00B03HD191": (5000, 4100), "ES0119199000": (2500, 2300),
                    "IS3N.DE": (1800, 1700), "VGEA.DE": (2100, 2300), "4GLD.DE": (1300, 900)}


def load_sample_portfolio() -> None:
    """Callback: a realistic example portfolio, so first-time visitors see every tab working."""
    pf = {k: {"value": float(v), "cost": float(c)} for k, (v, c) in SAMPLE_PORTFOLIO.items()}
    acc = account_instrument(t("Remunerated account"), 0.0225)
    st.session_state["accounts_seed"] = [{"Name": acc.symbol, "TAE %": 2.25, "Type": t("Account")}]
    st.session_state.pop("accounts_ed", None)
    pf[acc.symbol] = {"value": 3000.0, "cost": 3000.0}
    set_state("source", "live")
    save_portfolio(pf)


def clear_portfolio() -> None:
    save_portfolio({})


@st.dialog(t("Add to my portfolio"))
def add_position_dialog() -> None:
    demo_mode = st.session_state.get("source") == "demo"
    modes = ["catalog", "account"] if demo_mode else ["catalog", "search", "account"]
    mode_labels = {"catalog": t("From the list"), "search": t("Search any fund or ETF"),
                   "account": t("Account or deposit")}
    mode = st.segmented_control(t("What do you want to add?"), modes, default="catalog", key=lkey("dlg_mode"),
                                format_func=mode_labels.get) or "catalog"
    inst = None
    if mode == "catalog":
        pool = [i for i in CATALOG if not demo_mode or i.symbol in load_demo().prices.columns]
        sym = st.selectbox(t("Product"), [i.symbol for i in pool], index=None, key=lkey("dlg_sym"),
                           placeholder=t("Type to filter: MSCI World, Vanguard, gold, bonds..."),
                           format_func=lambda s_: f"{find(s_).display} · {t(find(s_).kind)} · {find(s_).name}")
        inst = find(sym) if sym else None
    elif mode == "search":
        q = st.text_input(t("Name, ISIN or ticker"), key="dlg_q", placeholder="Fidelity MSCI World, IE00B4L5Y983")
        if st.button(t("Search"), key="dlg_go") and q.strip():
            with st.spinner(t("Searching...")):
                try:
                    st.session_state["dlg_hits"] = [instrument_to_dict(h["instrument"]) for h in search_instruments(q)]
                except Exception:
                    st.session_state["dlg_hits"] = []
            if not st.session_state["dlg_hits"]:
                st.info(t("Nothing with price history found. Try another name or add it as your own fund."))
        hits = st.session_state.get("dlg_hits", [])
        if hits:
            k = st.selectbox(t("Results"), range(len(hits)), key=lkey("dlg_pick"),
                             format_func=lambda i: f"{hits[i]['name']} · {t(hits[i]['kind'])}")
            inst = instrument_from_dict(hits[k])
    else:
        name = st.text_input(t("Name"), value=t("Remunerated account"), key="dlg_acc_name")
        tae = st.number_input("TAE %", 0.0, 15.0, 2.0, 0.05, key="dlg_tae")
        kind = st.segmented_control(t("Type"), ["Account", "Deposit"], default="Account", key=lkey("dlg_kind"),
                                    format_func=t) or "Account"
        inst = account_instrument(name.strip() or t("Remunerated account"), tae / 100, kind) if name.strip() else None
    if inst is not None and mode != "account":
        st.markdown(f"<div class='pl-card'><b>{inst.name}</b><span class='pl-badge'>{t(inst.kind)}</span>"
                    f"<span class='pl-badge'>{t(inst.asset_class)}</span><br><small>TER {inst.ter * 100:.2f} %"
                    f" · {t(inst.management)}</small></div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    value = c1.number_input(t("Current value (€)"), 0.0, 1e9, 1000.0, 100.0, key="dlg_value")
    cost = c2.number_input(t("Amount you paid (€, optional)"), 0.0, 1e9, 0.0, 100.0, key="dlg_cost",
                           help=t("Used for the gain and the tax estimate. Leave 0 if you do not know it."))
    if st.button(t("Add to my portfolio"), type="primary", disabled=inst is None or value <= 0, width="stretch"):
        add_to_portfolio(inst, value, cost)
        st.rerun()


def resolve_holding_key(key: str) -> str | None:
    """Old sessions stored holdings by display label; map a label or identifier to a symbol."""
    inst = find(key)
    if inst is not None:
        return inst.symbol
    for i in CATALOG:
        if i.display == key or i.short == key:
            return i.symbol
    for sym_, d_ in st.session_state.get("added", {}).items():
        if instrument_from_dict(d_).display == key:
            return sym_
    if any(r.get("Name") == key for r in st.session_state.get("accounts_seed", [])):
        return key
    return key if " " not in key else None


def apply_import(df: pd.DataFrame) -> None:
    """Turn imported positions into the app's universe and holdings (runs before the widgets are built)."""
    catalog_syms, added, accounts, seed, missing = [], {}, [], {}, []
    for r in df.itertuples(index=False):
        rate = float(r.rate) if pd.notna(r.rate) else None
        if r.kind in ("Account", "Deposit") or (rate is not None and not r.identifier):
            name = r.name or r.identifier or t("Account")
            inst = account_instrument(name, rate or 0.0, r.kind or "Account")
            accounts.append({"Name": name, "TAE %": round((rate or 0.0) * 100, 3), "Type": t(inst.kind)})
        else:
            inst = find(r.identifier) if r.identifier else None
            if inst is None or inst.symbol not in CATALOG_SYMBOLS:
                try:
                    hits = search_instruments(r.identifier or r.name, max_results=1)
                except Exception:
                    hits = []
                if not hits:
                    missing.append(r.identifier or r.name)
                    continue
                inst = hits[0]["instrument"]
                if r.name and inst.symbol not in CATALOG_SYMBOLS and len(r.name) <= 40:
                    inst = replace(inst, name=r.name, short=r.name[:28])
            if inst.symbol in CATALOG_SYMBOLS:
                catalog_syms.append(inst.symbol)
            else:
                added[inst.symbol] = instrument_to_dict(inst)
        seed[inst.symbol] = {"value": float(r.value), "cost": float(r.cost)}
    for name_, val_ in (("source", "live"), ("preset", "(custom)"), ("catalog_assets", [])):
        set_state(name_, val_)
    st.session_state.update({"_preset": "(custom)", "extra": "", "added": added, "accounts_seed": accounts})
    save_portfolio(seed)
    for stale in ("inst", "mu_edit", "accounts_ed"):
        st.session_state.pop(stale, None)
    msg = t("Imported {n} positions.").format(n=len(seed))
    if missing:
        msg += " " + t("Not found (add them as your own fund): {m}").format(m=", ".join(missing))
    st.session_state["_import_msg"] = msg


def sidebar():
    for k_, v_ in DEFAULTS.items():
        st.session_state.setdefault(k_, v_)
    sb = st.sidebar

    # ---------------- 1. My portfolio
    sb.markdown(f"<div class='pl-sec'>{t('My portfolio')}</div>", unsafe_allow_html=True)
    pf_now = current_portfolio()
    if sb.button(t("Add to my portfolio"), type="primary", width="stretch", key="sb_add", icon=":material/add:"):
        add_position_dialog()
    if pf_now:
        total_ = sum(v["value"] for v in pf_now.values())
        sb.caption(t("My portfolio: {n} positions · {v}").format(n=len(pf_now), v=money(total_, "EUR")))
    else:
        sb.caption(t("Build your portfolio product by product, import it from a file or try the example."))
    files_box = sb.expander(t("Import a portfolio or load a session"), icon=":material/upload_file:")
    session = files_box.file_uploader(t("Load a saved session (.json)"), type=["json"], key="session_file",
                               help=t("Restores your universe, holdings and settings."))
    if session is not None and st.session_state.get("_loaded") != session.file_id:
        cfg = json.loads(session.getvalue())
        for k, v in cfg.get("widgets", {}).items():
            if k == "lang":
                st.session_state["_lang_next"] = v
                continue
            if k == "source" and v not in ("live", "demo"):
                v = "demo" if "demo" in str(v).lower() else "live"
            if k in LANG_WIDGETS:
                set_state(k, v)
            else:
                st.session_state[k] = v
        st.session_state["custom_seed"] = cfg.get("custom_funds", [])
        st.session_state["added"] = cfg.get("added", {})
        st.session_state["accounts_seed"] = cfg.get("accounts", [])
        pf = cfg.get("portfolio")
        if pf is None:                            # sessions saved before v2.2 keyed holdings by label
            pf = {}
            for k_, v_ in cfg.get("holdings", {}).items():
                sym_ = resolve_holding_key(k_)
                if sym_ and (v_.get("value") or v_.get("cost")):
                    pf[sym_] = {"value": float(v_.get("value", 0)), "cost": float(v_.get("cost", 0))}
        save_portfolio(pf)
        for stale in ("holdings", "inst", "mu_edit", "groups", "custom_funds", "cma_edit", "accounts_ed"):
            st.session_state.pop(stale, None)
        st.session_state["_loaded"] = session.file_id
        st.rerun()

    imported = files_box.file_uploader(t("Import a portfolio (CSV or Excel)"), type=["csv", "xlsx", "xls"], key="pf_import",
                                help=t("Columns are detected automatically (ISIN or ticker, name, value, cost, type, "
                                       "TAE). Download a template from the My portfolio tab."))
    if imported is not None and st.session_state.get("_imported") != imported.file_id:
        st.session_state["_imported"] = imported.file_id
        try:
            with st.spinner(t("Reading the portfolio and finding each product...")):
                apply_import(parse_portfolio(imported.getvalue(), imported.name))
        except Exception as exc:
            st.session_state["_import_msg"] = t("Could not import the file: {err}").format(err=exc)
        st.rerun()


    # ---------------- 2. Compare with
    sb.markdown(f"<div class='pl-sec'>{t('Compare with')}</div>", unsafe_allow_html=True)
    demo = st.session_state.get("source") == "demo"
    customs: list[Instrument] = []
    if demo:
        demo_cols = list(load_demo().prices.columns)
        st.session_state.setdefault("demo_assets", [])
        chosen = sb.multiselect(t("Products to compare"), demo_cols, key="demo_assets",
                                placeholder=t("None selected"))
        extra, upload, base = [], None, "EUR"
    else:
        preset = sb.selectbox(t("Ready-made selection"), ["(custom)"] + list(PRESETS), key=lkey("preset"),
                              format_func=lambda p_: t("None") if p_ == "(custom)" else t(p_),
                              help=t("Loads a typical set of products to compare. Your own positions are always "
                                     "included."))
        options = [i.symbol for i in CATALOG]
        labels = {i.symbol: f"{i.display} · {t(i.kind)}" for i in CATALOG}
        if preset in PRESETS and st.session_state.get("_preset") != preset:
            set_state("catalog_assets", list(PRESETS[preset]))
        st.session_state["_preset"] = preset
        chosen = sb.multiselect(t("Products to compare"), options, format_func=lambda s: labels.get(s, s),
                                key=lkey("catalog_assets"), placeholder=t("Choose ETFs, funds..."))
        with sb.expander(t("Search funds, ETFs and shares"), icon=":material/search:"):
            st.caption(t("Searches Yahoo Finance by name, ISIN or ticker and keeps only products with price history. "
                         "The classification is guessed and can be edited in the instrument table."))
            q = st.text_input(t("Name, ISIN or ticker"), key="search_q",
                              placeholder="Fidelity MSCI World, IE00B4L5Y983, Apple")
            if st.button(t("Search"), key="search_go") and q.strip():
                with st.spinner(t("Searching...")):
                    try:
                        st.session_state["search_hits"] = [
                            {**{k: v for k, v in h.items() if k != "instrument"},
                             "instrument": instrument_to_dict(h["instrument"])} for h in search_instruments(q)]
                    except Exception as exc:
                        st.session_state["search_hits"] = []
                        st.warning(t("Search failed: {err}").format(err=exc))
                if not st.session_state["search_hits"]:
                    st.info(t("Nothing with price history found. Try another name or add it as your own fund."))
            hits = st.session_state.get("search_hits", [])
            if hits:
                def _hit_label(i):
                    h = hits[i]
                    kind = t(h["instrument"]["kind"])
                    since = f" · {t('since')} {h['start'][:4]}" if h["start"] else ""
                    return f"{h['name']} · {kind} · {h['exchange']}{since}"
                choice = st.selectbox(t("Results"), range(len(hits)), format_func=_hit_label, key=lkey("search_pick"))
                if st.button(t("Add to the universe"), key="search_add"):
                    inst = instrument_from_dict(hits[choice]["instrument"])
                    if inst.symbol in CATALOG_SYMBOLS:
                        set_state("catalog_assets", list(dict.fromkeys(
                            st.session_state.get("catalog_assets", []) + [inst.symbol])))
                    else:
                        st.session_state.setdefault("added", {})[inst.symbol] = instrument_to_dict(inst)
                    st.success(t("Added: {n}").format(n=inst.name))
            added = st.session_state.get("added", {})
            if added:
                keep = st.multiselect(t("Added by search or import"), list(added), default=list(added),
                                      format_func=lambda s_: instrument_from_dict(added[s_]).display)
                if set(keep) != set(added):
                    st.session_state["added"] = {k_: v_ for k_, v_ in added.items() if k_ in keep}
                    st.rerun()

    if not demo:
        with sb.expander(t("Add a fund that is not on the list"), icon=":material/add_box:"):
            st.caption(t("For funds Yahoo does not cover well (for example some Amundi or Carmignac funds). "
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

    # ---------------- 3. Cash
    with sb.expander(t("Remunerated accounts and deposits"), icon=":material/savings:"):
        st.caption(t("Add cash at a known interest rate. Forecasts use the TAE; the history follows the ECB rate "
                     "(via the €STR) with today's spread, never below zero."))
        seed_acc = pd.DataFrame(st.session_state.get("accounts_seed") or [], columns=ACCOUNT_COLUMNS)
        seed_acc["TAE %"] = pd.to_numeric(seed_acc["TAE %"], errors="coerce")
        acc_df = st.data_editor(
            seed_acc, num_rows="dynamic", key="accounts_ed", hide_index=True,
            column_config={"Name": st.column_config.TextColumn(t("Name")),
                           "TAE %": st.column_config.NumberColumn("TAE %", min_value=0.0, max_value=15.0, step=0.05),
                           "Type": st.column_config.SelectboxColumn(t("Type"), options=[t("Account"), t("Deposit")])})
        accounts = []
        for _, r in acc_df.iterrows():
            name = str(r.get("Name") or "").strip()
            if name and name.lower() != "nan" and pd.notna(r.get("TAE %")):
                accounts.append(account_instrument(name, float(r["TAE %"]) / 100,
                                                   i18n.untranslate(str(r.get("Type") or t("Account")))))
        st.session_state["account_rows"] = acc_df.to_dict("records")


    # ---------------- 4. Advanced settings
    sb.markdown(f"<div class='pl-sec'>{t('Settings')}</div>", unsafe_allow_html=True)
    with sb.expander(t("Data"), icon=":material/database:"):
        source = st.radio(t("Data source"), ["live", "demo"], key=lkey("source"),
                          format_func={"live": t("Yahoo Finance (live)"), "demo": t("Offline demo dataset")}.get,
                          help=t("The demo dataset ships with the repo (8 UCITS products in EUR, 2018-2026) and works "
                                 "without internet."))
        demo = source == "demo"
        if not demo:
            base = st.selectbox(t("Base currency"), ["EUR", "USD", "GBP", "CHF"], key="base",
                                help=t("Every price is converted to this currency with daily FX rates, so returns "
                                       "include the currency risk you actually bear."))
            extra_txt = st.text_input(t("Other Yahoo tickers or ISINs (comma separated)"), key="extra",
                                      placeholder="AAPL, IE00B3RBWM25, MEUD.PA")
            extra = [x.strip() for x in extra_txt.split(",") if x.strip()]
            up = st.file_uploader(t("Your own NAV history (CSV)"), type=["csv"], key="nav_csv",
                                  help=t("First column = date, then one column per fund, prices in the base currency. "
                                         "Semicolons and decimal commas are fine."))
            upload = up.getvalue() if up is not None else None
    with sb.expander(t("Period and data quality"), icon=":material/date_range:"):
        start = st.date_input(t("Start"), key="start")
        end = st.date_input(t("End"), key="end")
        backfill = st.checkbox(t("Backfill short fund histories with an ETF on the same index"), key="backfill",
                               disabled=demo)
        clean = st.checkbox(t("Remove one-day bad prints"), key="clean", disabled=demo)

    with sb.expander(t("Estimation"), icon=":material/functions:"):
        freq = st.selectbox(t("Return frequency"), list(PERIODS_PER_YEAR), key=lkey("freq"), format_func=t,
                            help=t("Weekly avoids the bias from exchanges closing at different times."))
        r_method = st.selectbox(t("Expected returns"), list(RETURN_METHODS), key=lkey("r_method"),
                                format_func=lambda m: t(RETURN_METHODS[m]),
                                help=t("Long-term forecasts use forward-looking assumptions per asset class instead "
                                       "of extrapolating the past. Edit them in the Optimiser tab."))
        alpha = st.number_input(t("Expected alpha of active funds (annual %)"), -3.0, 3.0, step=0.25, key="alpha",
                                help=t("Extra return you expect from active managers before fees. The evidence "
                                       "(SPIVA) suggests about zero: most active funds trail their index by their "
                                       "fee difference.")) / 100
        c_method = st.selectbox(t("Covariance"), list(COV_METHODS), key=lkey("c_method"),
                                format_func=lambda m: t(COV_METHODS[m]))
        rf = st.number_input(t("Risk-free rate (annual %)"), step=0.25, key="rf",
                             help=t("Expected return of euro cash: 2.6% a year in J.P. Morgan's 2027 assumptions.")) / 100

    with sb.expander(t("Constraints"), icon=":material/tune:"):
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
                max_w=max_w, min_w=min_w, group_df=group_df, alpha=alpha, accounts=accounts,
                extras=customs + [instrument_from_dict(d_) for d_ in st.session_state.get("added", {}).values()]
                if not demo else [])




# =========================================================================== load data
cfg = sidebar()


def render_ticker() -> None:
    """Strip of reference markets with their daily change, like the header of a financial portal."""
    if cfg["demo"]:
        return
    snap = market_snapshot()
    if not snap:
        return
    items = []
    for name_, last_, chg_ in snap:
        cls = "pos" if chg_ >= 0 else "neg"
        arrow = "▲" if chg_ >= 0 else "▼"
        val = f"{last_:,.2f}" if last_ < 100 else f"{last_:,.0f}"
        if lang == "es":
            val = val.replace(",", "X").replace(".", ",").replace("X", ".")
        items.append(f"<div><span class='n'>{name_}</span><b>{val}</b><span class='{cls}'>{arrow} {pct(chg_, 2)}</span>"
                     f"</div>")
    st.markdown(f"<div class='pl-ticker'>{''.join(items)}</div>", unsafe_allow_html=True)


def render_footer() -> None:
    year = date.today().year
    st.markdown(f"""
<div class='pl-foot'>
  <div><div class='pl-brand'><img src='data:image/svg+xml;base64,{_logo_b64}' style='width:30px;height:30px'/>
    <div class='n' style='font-size:1.05rem'>{APP_NAME}</div></div>
    <p class='d'>{t('Educational tool to build and analyse investment portfolios. It is not financial, investment '
                     'or tax advice: past returns and forecasts do not guarantee future results.')}</p></div>
  <div><div class='h'>{t('Data and sources')}</div>
    <a href='https://finance.yahoo.com' target='_blank'>Yahoo Finance</a>
    <a href='{JPM_URL}' target='_blank'>J.P. Morgan LTCMA 2027</a>
    <a href='https://www.justetf.com/es/' target='_blank'>justETF</a></div>
  <div><div class='h'>{t('Project')}</div>
    <a href='{REPO_URL}' target='_blank'>{t('Source code')}</a>
    <a href='{REPO_URL}#methods' target='_blank'>{t('Methodology')}</a>
    <a href='{REPO_URL}/blob/main/docs/guide.html' target='_blank'>{t('Technical guide')}</a></div>
  <div><div class='h'>{t('About')}</div>
    <a href='https://github.com/rodrisantana' target='_blank'>Rodrigo Santana</a>
    <span class='d'>© {year} · {t('Prices may be delayed. Use at your own risk.')}</span></div>
</div>""", unsafe_allow_html=True)


render_ticker()
hero_slot = st.container()


def render_hero(kpis: list[tuple[str, str, str]] | None = None) -> None:
    k_html = "".join(f"<div class='kpi'><div class='l'>{l_}</div><div class='v {c_}'>{v_}</div></div>"
                     for l_, v_, c_ in (kpis or []))
    with hero_slot:
        st.markdown(f"<div class='pl-hero'><div><div class='tag' style='opacity:.75;text-transform:uppercase;"
                    f"letter-spacing:.1em;font-size:.72rem'>{t('My portfolio')}</div>"
                    f"<h1>{t('Overview')}</h1></div><div class='kpis'>{k_html}</div></div>", unsafe_allow_html=True)


def render_landing() -> None:
    lead = t("Build your portfolio with any ETF, index or active fund, bond fund or savings account, see what you can "
             "expect at every horizon and compare it with the strategies professionals use.")
    st.markdown(f"<h1 style='font-size:2.4rem;font-weight:800;letter-spacing:-.02em;margin:8px 0 4px 0'>"
                f"{t('Your investments, clearly.')}</h1><p style='font-size:1.1rem;opacity:.75;max-width:62ch'>"
                f"{lead}</p>", unsafe_allow_html=True)
    tiles = [("#0E8F82", "1", t("Build your portfolio"),
              t("Add what you own, product by product, with its current value.")),
             ("#2a78d6", "2", t("Import a file"),
              t("Upload a CSV or Excel export from your bank or broker; columns are detected automatically.")),
             ("#6250d6", "3", t("Explore an example"),
              t("See every feature working with a realistic diversified portfolio."))]
    cols = st.columns(3)
    for col, (color, num, title, body) in zip(cols, tiles):
        col.markdown(f"<div class='pl-tile'><div class='ic' style='background:{color}'>{num}</div><h4>{title}</h4>"
                     f"<p>{body}</p></div>", unsafe_allow_html=True)
    if cols[0].button(t("Add to my portfolio"), type="primary", width="stretch", key="land_add"):
        add_position_dialog()
    up_ = cols[1].file_uploader(t("Import a portfolio (CSV or Excel)"), type=["csv", "xlsx", "xls"], key="land_import",
                                label_visibility="collapsed")
    if up_ is not None and st.session_state.get("_imported") != up_.file_id:
        st.session_state["_imported"] = up_.file_id
        try:
            with st.spinner(t("Reading the portfolio and finding each product...")):
                apply_import(parse_portfolio(up_.getvalue(), up_.name))
        except Exception as exc:
            st.session_state["_import_msg"] = t("Could not import the file: {err}").format(err=exc)
        st.rerun()
    cols[2].button(t("Load an example portfolio"), on_click=load_sample_portfolio, width="stretch",
                   key="land_sample")
    st.caption(t("Tip: in the sidebar you can also pick products just to compare them, without adding them to your "
                 "portfolio."))


if st.session_state.get("_import_msg"):
    st.info(st.session_state.pop("_import_msg"))
user_instruments = cfg["extras"] + cfg["accounts"]
for inst in user_instruments:
    register(inst)
custom_spec = json.dumps([instrument_to_dict(i) for i in user_instruments], sort_keys=True, default=list)
portfolio_syms = [s_ for s_ in current_portfolio()
                  if not cfg["demo"] or s_ in load_demo().prices.columns or describe(s_).rate is not None]
ids = list(dict.fromkeys(cfg["chosen"] + cfg["extra"] + [i.symbol for i in user_instruments] + portfolio_syms))
if len(ids) < 2 and not cfg["upload"]:
    if ids:
        st.info(t("Add at least one more product to start the analysis."))
    render_landing()
    render_footer()
    st.stop()

try:
    with st.spinner(t("Downloading prices and converting currencies...")):
        if cfg["demo"]:
            d = load_demo()
            cols = [c for c in ids if c in d.prices.columns]
            px = d.prices[cols].copy()
            synth = {}
            for acc in cfg["accounts"]:
                px[acc.symbol] = account_series(d.prices["XEON.DE"], acc.rate).reindex(px.index)
                synth[acc.symbol] = "€STR (XEON.DE) + spread"
            data = PriceData(px, "EUR", {c: "EUR" for c in px.columns}, {c: c for c in px.columns}, synthetic=synth)
        else:
            data = get_prices(tuple(ids), cfg["base"], cfg["backfill"], cfg["clean"], cfg["upload"], custom_spec)
except Exception as exc:
    st.error(t("Could not load prices: {err}").format(err=exc))
    st.caption(t("Tip: switch to the offline demo dataset, or check the ticker on finance.yahoo.com."))
    render_footer()
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


def instrument_link(asset: str) -> str | None:
    """justETF for exchange-traded products with an ISIN, otherwise the Yahoo Finance quote page."""
    ident = inv_label[asset]
    inst = base_meta[ident]
    if inst.kind in ("ETF", "ETC", "ETN") and is_isin(inst.isin):
        return f"https://www.justetf.com/es/etf-profile.html?isin={inst.isin}"
    symbol = data.resolved.get(ident)
    return f"https://finance.yahoo.com/quote/{symbol}" if symbol and " " not in symbol else None


def data_status(asset: str) -> str:
    ident = inv_label[asset]
    if ident in data.synthetic:
        return t("Simulated from {p}").format(p=data.synthetic[ident])
    if ident in data.backfilled:
        return t("Real + backfilled with {p}").format(p=data.backfilled[ident])
    return t("Real")


# ---------------------------------------------------------------- instrument table (classification and TER editable)
_t_mine, _t_plan, _t_opt, _t_prod, _t_bt, _t_guide = st.tabs(
    [t("My portfolio"), t("Savings plan"), t("Optimiser"), t("Products"), t("Backtest"), t("Guide and methodology")])
tabs = [_t_guide, _t_prod, _t_opt, _t_mine, _t_plan, _t_bt, _t_guide]
with tabs[0]:
    st.markdown(i18n.GUIDE[lang])
    st.subheader(t("The strategies, explained"))
    for name_ in STRATEGIES:
        with st.expander(t(name_)):
            st.markdown(i18n.STRATEGY_HELP[lang][name_])
    st.subheader(t("Glossary"))
    st.markdown(i18n.GLOSSARY[lang])
with tabs[1]:
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
        "Link": [instrument_link(a) for a in assets],
    })
    inst_df = st.data_editor(
        inst_df, hide_index=True, key="inst", disabled=["Asset", "Name", "Data", "Quote ccy", "Link"],
        column_config={
            "Asset": st.column_config.TextColumn(t("Asset")), "Name": st.column_config.TextColumn(t("Name")),
            "Type": st.column_config.SelectboxColumn(t("Type"), options=[t(k) for k in KINDS]),
            "Management": st.column_config.SelectboxColumn(t("Management"), options=[t(m) for m in MANAGEMENT]),
            "Class": st.column_config.SelectboxColumn(t("Class"), options=[t(c) for c in ASSET_CLASSES + (MIXED,)]),
            "Region": st.column_config.SelectboxColumn(t("Region"), options=[t(r) for r in REGIONS]),
            "TER %": st.column_config.NumberColumn("TER %", format="%.2f", min_value=0.0, max_value=5.0, step=0.01),
            "Data": st.column_config.TextColumn(t("Data")), "Quote ccy": st.column_config.TextColumn(t("Quote ccy")),
            "Link": st.column_config.LinkColumn(t("Factsheet"), display_text=t("open")),
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
rf = cfg["rf"]
cash_rates = {a: meta[a].rate for a in assets if meta[a].rate is not None}
if cash_rates and max(cash_rates.values()) > rf:
    rf = max(cash_rates.values())
    st.info(t("Your best account pays {r}, so it is used as the risk-free rate: risky assets must beat it.").format(
        r=pct(rf, 2)))

# ---------------------------------------------------------------- estimation
cov, hist_mu, est_info = get_estimates(returns, ppy, cfg["c_method"])
cov = estimators.floor_volatility(cov, 0.002)       # accounts and money-market funds are nearly riskless
with tabs[2]:
    cma = dict(DEFAULT_CMA)
    if cfg["r_method"] == "long_term":
        with st.expander(t("Long-term assumptions by asset class (editable)")):
            st.caption(t("Expected annual returns in EUR for the next 10-15 years, before fees. By default they are the "
                         "euro figures of J.P. Morgan's 2027 Long-Term Capital Market Assumptions; rows marked 'own' "
                         "are not in the report. The optimiser and the Monte Carlo use the mean return; the compound "
                         "return is what a buy-and-hold investor typically earns per year. Each asset gets the figure "
                         "of its class and region minus its TER (plus alpha for active funds). Volatilities and "
                         "correlations come from the data."))
            cma_preset = st.selectbox(t("Set of assumptions"), list(CMA_PRESETS), key=lkey("cma_preset"), format_func=t)
            base_tab = preset_table(cma_preset)
            show_tab = base_tab.assign(Assumption=[t(k) for k in base_tab["Assumption"]])
            cma_df = st.data_editor(
                show_tab, hide_index=True, key=f"cma_edit_{cma_preset}",
                disabled=["Assumption", "Compound %", "Source"],
                column_config={"Assumption": st.column_config.TextColumn(t("Assumption")),
                               "Mean %": st.column_config.NumberColumn(t("Mean %"), format="%.2f", step=0.25),
                               "Compound %": st.column_config.NumberColumn(t("Compound %"), format="%.2f"),
                               "Source": st.column_config.TextColumn(t("Source"))})
            cma = {k: float(v) / 100 for k, v in zip(base_tab["Assumption"], cma_df["Mean %"])}
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
    portfolios, frontier = get_portfolios(mu, cov, rf, spec)
except InfeasibleError as exc:
    st.error(t("Constraints are infeasible: {err}").format(err=exc))
    st.stop()

# ---------------------------------------------------------------- holdings (built with the dialog, edited here)
with tabs[3]:
    pf_top = st.container()
    pf_base = st.session_state.get("portfolio", {})
    pf_rows = pd.DataFrame({
        "Symbol": list(pf_base),
        "Product": [describe(s_).display for s_ in pf_base],
        "Value": [float(v["value"]) for v in pf_base.values()],
        "Cost basis": [float(v["cost"]) for v in pf_base.values()],
    })
    if len(pf_rows):
        with st.expander(t("Edit amounts or remove positions"), icon=":material/edit:"):
            st.caption(t("Change the value or the amount paid, or select a row and press delete to remove it."))
            pf_rows = st.data_editor(
                pf_rows, hide_index=True, key="pf_ed", num_rows="delete", disabled=["Symbol", "Product"],
                column_order=["Product", "Value", "Cost basis"],
                column_config={"Product": st.column_config.TextColumn(t("Product")),
                               "Value": st.column_config.NumberColumn(t("Market value ({c})").format(c=ccy),
                                                                      min_value=0.0, step=100.0, format="%.2f"),
                               "Cost basis": st.column_config.NumberColumn(t("Cost basis ({c})").format(c=ccy),
                                                                           min_value=0.0, step=100.0, format="%.2f")})
            st.button(t("Remove all positions"), on_click=clear_portfolio, key="pf_clear")
    st.session_state["_pf_effective"] = {
        sym_: {"value": float(v_ or 0), "cost": float(c_ or 0)}
        for sym_, v_, c_ in zip(pf_rows["Symbol"], pf_rows["Value"], pf_rows["Cost basis"])}
holdings = []
missing_pos = []
for sym_, v_ in st.session_state["_pf_effective"].items():
    lab = label.get(sym_)
    if lab is None:
        missing_pos.append(describe(sym_).display)
        continue
    holdings.append(Holding(lab, float(v_["value"]), float(v_["cost"])))
has_holdings = sum(h.value for h in holdings) > 0
plan = None
opt_eval = PortfolioOptimizer(mu, cov, rf)
if has_holdings:
    my_w = pd.Series({h.asset: h.value for h in holdings}).reindex(assets).fillna(0.0)
    portfolios = {**portfolios, "My portfolio": opt_eval.evaluate((my_w / my_w.sum()).values, "My portfolio")}
    _me = portfolios["My portfolio"]
    _tot = sum(h.value for h in holdings)
    _cost = sum(h.cost_basis for h in holdings)
    _g = (_tot / _cost - 1) if _cost else None
    render_hero([(t("Value"), money(_tot, ccy), ""),
                 (t("Unrealised gain"), pct(_g) if _g is not None else "n/a",
                  "" if _g is None else ("pos" if _g >= 0 else "neg")),
                 (t("Expected return"), pct(_me.expected_return), ""),
                 (t("Volatility"), pct(_me.volatility), "")])
else:
    pass                                        # no hero card until the user has a portfolio


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
with tabs[1]:
    stats = M.summary_table(prices.pct_change().dropna(), 252, rf)
    stats.insert(0, "TER", ter)
    st.subheader(t("Historical performance (daily data, in {c})").format(c=ccy))
    if data.synthetic:
        st.caption(t("Simulated funds show their proxy's history minus fees, not the fund's own record."))
    fmt = {c: "{:.2%}" for c in stats.columns}
    fmt.update({"Sharpe": "{:.2f}", "Sortino": "{:.2f}", "Calmar": "{:.2f}", "Longest drawdown (days)": "{:.0f}"})
    st.dataframe(styled(tr_columns(stats), {t(k): v for k, v in fmt.items()}), width="stretch")
    log = st.toggle(t("Log scale"), value=True, key="log_overview")
    st.subheader(t("Growth of 100 invested"))
    st.caption(t("What 100 euros invested at the start became in each asset, dividends included and already net of "
                 "the fund's fees. The log scale makes equal percentage moves look equal."))
    st.plotly_chart(charts.growth_chart(prices / prices.iloc[0] * 100, asset_colors, log, ""), width="stretch")
    st.subheader(t("Falls from the peak (drawdowns)"))
    st.caption(t("How far each asset was below its previous high at every moment. -30% means it had lost 30% from "
                 "its best value so far; the line returns to 0% when the loss is fully recovered. Deep and long dips "
                 "are what test an investor's nerves."))
    st.plotly_chart(charts.drawdown_chart(prices, asset_colors), width="stretch")
    a, b = st.columns(2)
    with a:
        st.subheader(t("Correlation"))
        st.caption(t("1 = they move together, 0 = unrelated, negative = they tend to move in opposite directions. "
                     "Mixing assets with low correlation lowers the risk of the whole."))
        st.plotly_chart(charts.correlation_heatmap(estimators.cov_to_corr(cov)), width="stretch")
    with b:
        st.subheader(t("Calendar-year returns"))
        st.caption(t("Return of each asset in each calendar year (the first year may be partial). Blue = gain, red = "
                     "loss."))
        st.plotly_chart(charts.calendar_heatmap(M.calendar_year_returns(prices)), width="stretch")
    notes = [f"**{a_}**: {t(meta[a_].note)}" for a_ in assets if meta[a_].note]
    if notes:
        with st.expander(t("Notes on the instruments")):
            st.markdown("\n\n".join(notes))

# =========================================================================== Optimiser tab
with tabs[2]:
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
            custom = PortfolioOptimizer(mu, cov, rf, _constraints_from_json(spec)).efficient_risk(target_vol)
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
        st.caption(t("Each point is a portfolio: further right means more risk (volatility), higher means more "
                     "expected return. The green curve is the efficient frontier: the best return you can expect for "
                     "each level of risk. Diamonds are the strategies; the star is your portfolio. Grey dots are random "
                     "portfolios, to show how much worse a careless mix can be."))
        st.plotly_chart(charts.efficient_frontier(
            frontier, shown, mu, pd.Series(np.sqrt(np.diag(cov.values)), index=assets), rf,
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
    with st.expander(t("What does each strategy mean?")):
        for name_ in STRATEGIES:
            st.markdown(f"**{t(name_)}**. " + i18n.STRATEGY_HELP[lang][name_].split("\n\n")[0])
    pick = st.multiselect(t("Portfolios"), list(shown), format_func=t,
                          default=[n for n in ("Maximum Sharpe", "Risk parity", "My portfolio") if n in shown],
                          key=f"w_pick_{len(shown)}_{lang}")
    if pick:
        wdf = pd.DataFrame({n: shown[n].weights for n in pick})
        st.plotly_chart(charts.weights_bars(wdf, charts.color_map(list(shown))), width="stretch")
        render_breakdown({n: shown[n].weights for n in pick}, "opt")
        st.download_button(t("Download weights (CSV)"), tr_columns(wdf).to_csv().encode(), "weights.csv", "text/csv")

    st.subheader(t("Where does the risk come from?"))
    focus = st.selectbox(t("Portfolio"), list(shown), format_func=t, key=f"rc_pick_{len(shown)}_{lang}")
    rc = risk_contributions(shown[focus].weights, cov)
    st.plotly_chart(charts.risk_vs_weight(shown[focus].weights, rc), width="stretch")
    st.caption(t("Risk contribution = share of portfolio variance coming from each asset. In a typical 60/40 "
                 "portfolio equities bring around 90% of the risk."))

# =========================================================================== My portfolio tab
with pf_top:
    h1, h2 = st.columns([3, 1], vertical_alignment="bottom")
    h1.subheader(t("My portfolio"))
    if h2.button(t("Add to my portfolio"), type="primary", width="stretch", key="tab_add", icon=":material/add:"):
        add_position_dialog()
    if missing_pos:
        st.warning(t("No price data for: {m}. They are left out of the analysis.").format(m=", ".join(missing_pos)))
    if not has_holdings:
        _msg = t("Press Add to my portfolio to choose a fund, ETF or account and type how much you have in it. You "
                 "can also import a CSV or Excel file from the sidebar, or load an example to explore.")
        st.markdown(f"<div class='pl-empty'><h3>{t('Your portfolio is empty')}</h3><p>{_msg}</p></div>",
                    unsafe_allow_html=True)
        st.button(t("Load an example portfolio"), on_click=load_sample_portfolio, key="tab_sample")
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
        k[4].metric(t("Annual cost (TER)"), money(float(me.weights @ ter) * total, ccy),
                    f"TER {pct(float(me.weights @ ter), 2)}", delta_color="off", delta_arrow="off")
        st.plotly_chart(charts.allocation_strip(tr_index(breakdown_table({"m": me.weights}, meta, "Asset class")["m"])),
                        width="stretch", key="strip_mine", config={"displayModeBar": False})
        pos = pd.DataFrame([{
            "Product": h.asset, "Type": t(meta[h.asset].kind), "Class": t(meta[h.asset].asset_class),
            "Value": h.value, "Weight": h.value / total,
            "Gain": (h.value - h.cost_basis) if h.cost_basis else np.nan,
            "Gain %": (h.value / h.cost_basis - 1) if h.cost_basis else np.nan} for h in holdings]
        ).sort_values("Value", ascending=False)

        def _pl_color(v):
            if pd.isna(v):
                return ""
            return "color: #0E9F6E; font-weight: 600" if v >= 0 else "color: #D64545; font-weight: 600"

        st.dataframe(
            styled(pos, {"Value": "{:,.0f}", "Gain": "{:+,.0f}", "Gain %": "{:+.1%}"}, na_rep="-")
            .map(_pl_color, subset=["Gain", "Gain %"]),
            hide_index=True, width="stretch",
            column_config={"Product": st.column_config.TextColumn(t("Product")),
                           "Type": st.column_config.TextColumn(t("Type")),
                           "Class": st.column_config.TextColumn(t("Class")),
                           "Value": st.column_config.NumberColumn(t("Value")),
                           "Weight": st.column_config.ProgressColumn(t("Weight"), format="percent", min_value=0,
                                                                     max_value=1),
                           "Gain": st.column_config.NumberColumn(t("Gain")),
                           "Gain %": st.column_config.NumberColumn(t("Gain %"))})

with tabs[3]:
    if has_holdings:
        try:
            same_risk = PortfolioOptimizer(mu, cov, rf, _constraints_from_json(spec)).efficient_risk(
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
                                   key=lkey("target_pick"))
        new_cash = c2.number_input(t("New money to invest ({c})").format(c=ccy), value=1000.0, step=100.0,
                                   key="new_cash")
        sells = c3.toggle(t("Allow selling (full rebalance)"), value=False, key="sells",
                          help=t("Off: only the new money is used, nothing is sold and no tax is triggered."))
        target_w = shown[target_name].weights
        try:
            plan = rebalance_plan(holdings, target_w, new_cash, allow_sells=sells,
                                  is_fund={a: meta[a].tax_free_switch for a in assets})
        except ValueError as exc:
            st.error(str(exc))
            plan = None
        if plan is not None:
            plan_show = plan.copy()
            plan_show["Tax-free switch"] = plan_show["Tax-free switch"].map({True: t("yes"), False: t("no")})
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
    st.subheader(t("Import and export"))
    st.caption(t("Export your positions to CSV or Excel, edit them anywhere and import them again from the sidebar. "
                 "Works with any bank or broker: only an ISIN or ticker (or the name) and a value are needed."))
    exp = export_portfolio({h.asset: (h.value, h.cost_basis) for h in holdings if h.value or h.cost_basis}, meta)
    c = st.columns(3)
    c[0].download_button(t("Download portfolio (CSV)"), exp.to_csv(sep=";", decimal=",", index=False).encode("utf-8-sig"),
                         "cartera.csv", "text/csv", disabled=exp.empty)
    sheets = {t("Portfolio"): exp}
    if plan is not None:
        sheets[t("Rebalancing plan")] = tr_columns(plan.reset_index())
    sheets[t("Strategies")] = tr_columns(pd.DataFrame({t(n): p.weights for n, p in shown.items()}).reset_index())
    c[1].download_button(t("Download portfolio (Excel)"), to_excel_bytes(sheets), "cartera.xlsx",
                         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    c[2].download_button(t("Download an import template"), TEMPLATE.encode("utf-8-sig"), "plantilla_cartera.csv",
                         "text/csv")

    st.subheader(t("Save this session"))
    st.caption(t("Downloads your universe, settings, own funds and holdings so you can load them next time."))
    widget_keys = [k_ for k_ in DEFAULTS if k_ not in ("start", "end")] + ["demo_assets"]
    payload = {"widgets": {k_: st.session_state[k_] for k_ in widget_keys if k_ in st.session_state},
               "custom_funds": st.session_state.get("custom_rows", []),
               "added": st.session_state.get("added", {}),
               "accounts": st.session_state.get("account_rows", []),
               "portfolio": st.session_state.get("_pf_effective", {})}
    st.download_button(t("Download session (.json)"), json.dumps(payload, indent=2, default=str).encode(),
                       "portfolio_session.json", "application/json")

# =========================================================================== Savings plan tab
with tabs[4]:
    st.caption(t("Project a portfolio with monthly contributions. The expected path uses the long-term return; the "
                 "Monte Carlo shows the range of outcomes around it."))
    options = list(shown)
    default_idx = options.index("My portfolio") if "My portfolio" in options else 0
    c = st.columns(4)
    mc_name = c[0].selectbox(t("Portfolio"), options, index=default_idx, format_func=t, key=f"mc_pick_{len(options)}_{lang}")
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
    infl = c[3].number_input(t("Inflation (annual %)"), -2.0, 15.0, JPM_EUR_INFLATION * 100, 0.1, key="mc_infl",
                             help=t("2.2% is J.P. Morgan's long-term euro inflation assumption.")) / 100
    if exp_r > 0.08:
        st.caption(t("Heads-up: {r} a year is above the long-run nominal return of global equities (roughly 6-8%).")
                   .format(r=pct(exp_r)))
    c = st.columns(4)
    growth = c[0].number_input(t("Contribution growth (annual %)"), 0.0, 20.0, 0.0, 0.5, key="mc_growth") / 100
    goal = c[1].number_input(t("Goal in today's money ({c}, 0 = none)").format(c=ccy), 0.0, 1e10, 0.0, 10_000.0,
                             key="mc_goal")
    method = c[2].selectbox(t("Return model"), METHODS, key=lkey("mc_method"),
                            format_func=lambda m: t({"lognormal": "Log-normal", "student_t": "Student-t (fat tails)",
                                                     "bootstrap": "Historical block bootstrap"}[m]))
    n_sims = c[3].select_slider(t("Simulations"), [1000, 2000, 5000, 10000, 20000], value=5000, key="mc_n")
    real = st.toggle(t("Show in today's money (inflation-adjusted)"), value=True, key="mc_real")

    st.subheader(t("Expected path"))
    g_med = median_growth(exp_r - fee, vol)
    st.caption(t("The typical (median) path: half of the scenarios end above it and half below. It grows at {g} a "
                 "year, less than the {m} average return, because ups and downs eat into compound growth "
                 "(volatility drag).").format(g=pct(g_med, 2), m=pct(exp_r - fee, 2)))
    proj = projection_table(initial, monthly, years, g_med, growth, infl)
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
        st.caption(t("Thousands of possible futures. The dark band holds the middle half of the scenarios and the light "
                     "band 90% of them; the blue line is the median and the dotted line the money you put in. Thin "
                     "grey lines are individual scenarios: notice how bumpy each one is."))
        st.plotly_chart(charts.fan_chart(pct_df, contributed, goal or None, sample), width="stretch")
        st.caption(t("How the final value is distributed across all scenarios. The further right the tail, the more "
                     "the result depends on luck."))
        st.plotly_chart(charts.final_histogram(sim.final(real), float(contributed[-1]), goal or None), width="stretch")
        st.subheader(t("Return and money by horizon"))
        st.caption(t("For each holding period, the bar shows the range of average yearly returns across scenarios: "
                     "light = 80% of cases, dark = the middle half, dot = median. Over one year almost anything can "
                     "happen; over 20 years the range narrows a lot. Money columns include your contributions."))
        htab = horizon_table(sim, real=real)
        st.plotly_chart(charts.horizon_chart(htab), width="stretch")
        show_cols = ["Return P10", "Return P50", "Return P90", "Probability of a loss", "Contributed", "Money P10",
                     "Money P50", "Money P90"]
        hshow = htab[show_cols].rename(index=lambda y: f"{y} {t('years')}")
        hshow.index.name = None
        hfmt = {c_: "{:.1%}" for c_ in show_cols[:4]}
        hfmt.update({c_: "{:,.0f}" for c_ in show_cols[4:]})
        st.dataframe(styled(tr_columns(hshow), {t(k_): v for k_, v in hfmt.items()}), width="stretch")
        if goal and st.button(t("How much should I contribute each month to reach the goal?"), key="solve"):
            with st.spinner(t("Solving...")):
                res = {conf: required_contribution(inp, goal, conf, monthly_hist) for conf in (0.5, 0.75, 0.9)}
            st.table(pd.DataFrame({t("Probability of success"): ["50%", "75%", "90%"],
                                   t("Monthly contribution ({c})").format(c=ccy): [money(v, ccy) for v in res.values()]}))

# =========================================================================== Backtest tab
with tabs[5]:
    st.caption(t("Walk-forward: at every rebalance date each strategy is re-optimised using only the past "
                 "lookback years, then held until the next date. Prices are already net of each fund's TER; "
                 "trading costs are deducted on every rebalance."))
    c = st.columns(4)
    lookback = c[0].slider(t("Lookback (years)"), 1.0, 5.0, 3.0, 0.5, key="lookback")
    rebalance = c[1].selectbox(t("Rebalance"), [r for r in REBALANCE_RULES if r != "Never"], index=1, key=lkey("rebal"),
                               format_func=t)
    cost_bps = c[2].number_input(t("Trading cost (bps)"), 0.0, 100.0, 10.0, 1.0, key="cost_bps")
    bench = c[3].selectbox(t("Benchmark"), assets, index=0, key="bench")
    pool = list(STRATEGIES) + (["My portfolio"] if has_holdings else [])
    chosen_bt = st.multiselect(t("Strategies"), pool, format_func=t, key=f"bt_pick_{has_holdings}_{lang}",
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
                                             cfg["freq"], cfg["r_method"], cfg["c_method"], rf, spec)
            bench_name = f"{bench} ({t('buy and hold')})"
            bench_w = pd.Series(0.0, index=assets)
            bench_w[bench] = 1.0
            results[bench_name] = get_backtest(prices, "static", bench_name, bench_w, "Never", bt_start, cost_bps,
                                               lookback, cfg["freq"], cfg["r_method"], cfg["c_method"], rf, spec)
        wealth = pd.DataFrame({n: r.wealth for n, r in results.items()})
        colors = charts.color_map(list(wealth.columns))
        st.subheader(t("Growth of 100, out-of-sample"))
        st.caption(t("How each strategy would really have done if you had followed it, deciding every rebalance with "
                     "only the information available at the time."))
        st.plotly_chart(charts.growth_chart(wealth * 100, colors, False, ""), width="stretch")
        st.subheader(t("Falls from the peak (drawdowns)"))
        st.caption(t("The worst moments of each strategy: how much it was below its previous high."))
        st.plotly_chart(charts.drawdown_chart(wealth, colors), width="stretch")
        bench_r = wealth[bench_name].pct_change().dropna()
        rows = {}
        for n in wealth.columns:
            s = M.summary(wealth[n].pct_change().dropna(), 252, rf, bench_r)
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
            which = st.selectbox(t("Weights over time"), dyn, format_func=t, key=lkey("wot"))
            st.caption(t("How the strategy changed its allocation at each rebalance."))
            st.plotly_chart(charts.weights_over_time(results[which].weights, asset_colors), width="stretch")

# =========================================================================== Methodology tab
with tabs[6]:
    st.divider()
    st.markdown(i18n.METHODOLOGY[lang])

render_footer()
