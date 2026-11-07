"""Plotly figure builders shared by the Streamlit app and the HTML report.

Colour rules: a colour always follows the same entity (an asset or a
strategy keeps its colour on every chart and after any filter), sequential
data uses one hue, and the correlation map uses a blue/red diverging scale
with a neutral midpoint.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

# Validated categorical palette (colour-blind safe on adjacent pairs).
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
MUTED = "#898781"
INK = "#52514e"
GRID = "rgba(137,135,129,0.22)"
FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'

STRATEGY_COLORS = {
    "Maximum Sharpe": PALETTE[0],
    "Minimum variance": PALETTE[1],
    "Risk parity": PALETTE[2],
    "HRP": PALETTE[3],
    "Maximum diversification": PALETTE[4],
    "Equal weight": PALETTE[5],
    "Inverse volatility": PALETTE[6],
    "My portfolio": PALETTE[7],
}


def color_map(names: list[str]) -> dict[str, str]:
    """Stable colour per entity; past eight entities the rest share a muted grey."""
    out = {}
    for i, n in enumerate(names):
        out[n] = STRATEGY_COLORS.get(n) or (PALETTE[i] if i < len(PALETTE) else MUTED)
    return out


def _layout(fig: go.Figure, title: str = "", height: int = 420, pct_y: bool = False, pct_x: bool = False,
            legend: bool = True) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, x=0, xanchor="left", font=dict(size=15)),
        height=height, margin=dict(l=10, r=10, t=50 if title else 20, b=10),
        font=dict(family=FONT, size=12),
        hovermode="closest", showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1, bgcolor="rgba(0,0,0,0)"),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    axis = dict(showgrid=True, gridcolor=GRID, gridwidth=1, zeroline=False, linecolor=GRID)
    fig.update_xaxes(**axis, tickformat=".0%" if pct_x else None)
    fig.update_yaxes(**axis, tickformat=".0%" if pct_y else None)
    return fig


# --------------------------------------------------------------------------- frontier
def efficient_frontier(frontier, portfolios: dict, asset_mu: pd.Series, asset_vol: pd.Series,
                       risk_free_rate: float, cloud: pd.DataFrame | None = None,
                       asset_colors: dict[str, str] | None = None) -> go.Figure:
    fig = go.Figure()
    if cloud is not None and len(cloud):
        fig.add_trace(go.Scattergl(
            x=cloud["Volatility"], y=cloud["Return"], mode="markers", name="Random portfolios",
            marker=dict(size=4, color=MUTED, opacity=0.18), hoverinfo="skip"))
    fx = [p.volatility for p in frontier]
    fy = [p.expected_return for p in frontier]
    fig.add_trace(go.Scatter(
        x=fx, y=fy, mode="lines", name="Efficient frontier", line=dict(color=INK, width=2.5),
        customdata=np.array([[p.sharpe] for p in frontier]),
        hovertemplate="Volatility %{x:.1%}<br>Return %{y:.1%}<br>Sharpe %{customdata[0]:.2f}<extra>Frontier</extra>"))

    tangency = portfolios.get("Maximum Sharpe")
    if tangency is not None and tangency.volatility > 0:
        xmax = max(max(fx), float(asset_vol.max())) * 1.05
        slope = (tangency.expected_return - risk_free_rate) / tangency.volatility
        fig.add_trace(go.Scatter(
            x=[0, xmax], y=[risk_free_rate, risk_free_rate + slope * xmax], mode="lines",
            name="Capital market line", line=dict(color=MUTED, width=1.5, dash="dot"), hoverinfo="skip"))

    colors = asset_colors or color_map(list(asset_mu.index))
    fig.add_trace(go.Scatter(
        x=asset_vol.values, y=asset_mu.values, mode="markers+text", name="Assets",
        text=list(asset_mu.index), textposition="top center", textfont=dict(size=10, color=INK),
        marker=dict(size=9, color=[colors.get(a, MUTED) for a in asset_mu.index],
                    line=dict(width=2, color="white")),
        hovertemplate="<b>%{text}</b><br>Volatility %{x:.1%}<br>Return %{y:.1%}<extra></extra>"))

    cmap = color_map(list(portfolios))
    for name, p in portfolios.items():
        fig.add_trace(go.Scatter(
            x=[p.volatility], y=[p.expected_return], mode="markers", name=name,
            marker=dict(size=15, symbol="diamond" if name != "My portfolio" else "star",
                        color=cmap[name], line=dict(width=2, color="white")),
            hovertemplate=(f"<b>{name}</b><br>Volatility %{{x:.1%}}<br>Return %{{y:.1%}}"
                           f"<br>Sharpe {p.sharpe:.2f}<extra></extra>")))
    fig = _layout(fig, "", 520, pct_y=True, pct_x=True)
    xmax = max(max(fx), float(asset_vol.max())) * 1.12          # room for the asset labels
    ys = list(fy) + list(asset_mu.values) + [risk_free_rate]
    pad = (max(ys) - min(ys)) * 0.08
    fig.update_xaxes(title="Annualised volatility", range=[0, xmax])
    fig.update_yaxes(range=[min(ys) - pad, max(ys) + pad])
    fig.update_yaxes(title="Expected annual return")
    return fig


def weights_bars(weights: pd.DataFrame, colors: dict[str, str] | None = None, height: int = 380) -> go.Figure:
    """Grouped horizontal bars: one group per asset, one bar per portfolio."""
    weights = weights.loc[(weights > 1e-4).any(axis=1)]
    cmap = colors or color_map(list(weights.columns))
    fig = go.Figure()
    for col in weights.columns:
        fig.add_trace(go.Bar(
            y=weights.index, x=weights[col], name=col, orientation="h", marker_color=cmap.get(col, MUTED),
            marker_line_width=0,
            hovertemplate=f"<b>{col}</b><br>%{{y}}: %{{x:.1%}}<extra></extra>"))
    fig.update_layout(barmode="group", bargap=0.25, bargroupgap=0.08)
    fig = _layout(fig, "", max(height, 60 + 28 * len(weights) * max(1, len(weights.columns)) // 2), pct_x=True)
    fig.update_yaxes(autorange="reversed")
    return fig


def allocation_bar(weights: pd.Series, colors: dict[str, str], title: str = "") -> go.Figure:
    """Single portfolio, ranked bars with direct value labels."""
    w = weights[weights > 1e-4].sort_values(ascending=True)
    fig = go.Figure(go.Bar(
        x=w.values, y=w.index, orientation="h", marker_color=[colors.get(a, MUTED) for a in w.index],
        text=[f"{v:.1%}" for v in w.values], textposition="outside", cliponaxis=False,
        hovertemplate="%{y}: %{x:.2%}<extra></extra>"))
    fig = _layout(fig, title, 60 + 34 * len(w), pct_x=True, legend=False)
    fig.update_xaxes(range=[0, min(1.0, float(w.max()) * 1.25 + 0.02)])
    return fig


def risk_vs_weight(weights: pd.Series, risk: pd.Series) -> go.Figure:
    idx = weights[(weights > 1e-4) | (risk.abs() > 1e-4)].index
    fig = go.Figure()
    fig.add_trace(go.Bar(y=idx, x=weights[idx], name="Capital weight", orientation="h",
                         marker_color=PALETTE[0], hovertemplate="%{y}: %{x:.1%} of capital<extra></extra>"))
    fig.add_trace(go.Bar(y=idx, x=risk[idx], name="Risk contribution", orientation="h",
                         marker_color=PALETTE[1], hovertemplate="%{y}: %{x:.1%} of risk<extra></extra>"))
    fig.update_layout(barmode="group", bargap=0.3)
    fig = _layout(fig, "", 80 + 44 * len(idx), pct_x=True)
    fig.update_yaxes(autorange="reversed")
    return fig


# --------------------------------------------------------------------------- data views
def growth_chart(wealth: pd.DataFrame, colors: dict[str, str], log: bool = False, title: str = "") -> go.Figure:
    fig = go.Figure()
    for c in wealth.columns:
        fig.add_trace(go.Scatter(x=wealth.index, y=wealth[c], name=c, mode="lines",
                                 line=dict(width=2, color=colors.get(c, MUTED)),
                                 hovertemplate=f"<b>{c}</b> %{{y:,.2f}}<extra></extra>"))
    fig = _layout(fig, title, 440)
    fig.update_layout(hovermode="x unified")
    if log:
        fig.update_yaxes(type="log")
    return fig


def drawdown_chart(wealth: pd.DataFrame, colors: dict[str, str]) -> go.Figure:
    dd = wealth / wealth.cummax() - 1
    fig = go.Figure()
    for c in dd.columns:
        fig.add_trace(go.Scatter(x=dd.index, y=dd[c], name=c, mode="lines",
                                 line=dict(width=1.6, color=colors.get(c, MUTED)),
                                 hovertemplate=f"<b>{c}</b> %{{y:.1%}}<extra></extra>"))
    fig = _layout(fig, "", 320, pct_y=True)
    fig.update_layout(hovermode="x unified")
    return fig


def correlation_heatmap(corr: pd.DataFrame) -> go.Figure:
    z = corr.values
    text = [[f"{v:.2f}" for v in row] for row in z]
    fig = go.Figure(go.Heatmap(
        z=z, x=corr.columns, y=corr.index, zmin=-1, zmax=1, text=text, texttemplate="%{text}",
        textfont=dict(size=10),
        colorscale=[[0.0, "#2a78d6"], [0.5, "#f0efec"], [1.0, "#e34948"]],
        colorbar=dict(title="ρ", thickness=12),
        hovertemplate="%{y} / %{x}: %{z:.2f}<extra></extra>", xgap=2, ygap=2))
    fig = _layout(fig, "", 120 + 40 * len(corr), legend=False)
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False, autorange="reversed")
    return fig


def calendar_heatmap(yearly: pd.DataFrame) -> go.Figure:
    """Per-year returns, diverging around zero."""
    z = yearly.T.values
    lim = float(np.nanmax(np.abs(z))) if np.isfinite(z).any() else 1.0
    fig = go.Figure(go.Heatmap(
        z=z, x=[str(y) for y in yearly.index], y=list(yearly.columns), zmin=-lim, zmax=lim,
        text=[[("" if np.isnan(v) else f"{v:.0%}") for v in row] for row in z], texttemplate="%{text}",
        colorscale=[[0.0, "#e34948"], [0.5, "#f0efec"], [1.0, "#2a78d6"]], showscale=False,
        hovertemplate="%{y} %{x}: %{z:.1%}<extra></extra>", xgap=2, ygap=2))
    fig = _layout(fig, "", 90 + 36 * len(yearly.columns), legend=False)
    fig.update_xaxes(showgrid=False, side="top")
    fig.update_yaxes(showgrid=False, autorange="reversed")
    return fig


def weights_over_time(weights: pd.DataFrame, colors: dict[str, str]) -> go.Figure:
    fig = go.Figure()
    for c in weights.columns:
        if weights[c].max() < 1e-4:
            continue
        fig.add_trace(go.Scatter(x=weights.index, y=weights[c], name=c, mode="lines", stackgroup="w",
                                 line=dict(width=0.5, color=colors.get(c, MUTED)),
                                 hovertemplate=f"<b>{c}</b> %{{y:.1%}}<extra></extra>"))
    fig = _layout(fig, "", 340, pct_y=True)
    fig.update_layout(hovermode="x unified")
    fig.update_yaxes(range=[0, 1])
    return fig


# --------------------------------------------------------------------------- Monte Carlo
def fan_chart(pct: pd.DataFrame, contributed: np.ndarray, target: float | None = None,
              sample_paths: np.ndarray | None = None) -> go.Figure:
    x = pct.index
    fig = go.Figure()
    band = "rgba(42,120,214,{a})"
    if sample_paths is not None:
        for path in sample_paths:
            fig.add_trace(go.Scatter(x=x, y=path, mode="lines", line=dict(width=0.6, color="rgba(137,135,129,0.25)"),
                                     hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=x, y=pct["P95"], line=dict(width=0), hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=x, y=pct["P5"], fill="tonexty", fillcolor=band.format(a=0.14), line=dict(width=0),
                             name="5% to 95%", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=x, y=pct["P75"], line=dict(width=0), hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=x, y=pct["P25"], fill="tonexty", fillcolor=band.format(a=0.28), line=dict(width=0),
                             name="25% to 75%", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=x, y=pct["P50"], name="Median", line=dict(color=PALETTE[0], width=2.5),
                             customdata=np.stack([pct["P5"], pct["P95"], contributed], axis=1),
                             hovertemplate=("Median %{y:,.0f}<br>P5 %{customdata[0]:,.0f}"
                                            "<br>P95 %{customdata[1]:,.0f}<br>Contributed %{customdata[2]:,.0f}"
                                            "<extra></extra>")))
    fig.add_trace(go.Scatter(x=x, y=contributed, name="Money contributed", line=dict(color=INK, width=1.5, dash="dot"),
                             hoverinfo="skip"))
    if target:
        fig.add_hline(y=target, line=dict(color=PALETTE[1], width=1.5),
                      annotation_text="Goal", annotation_position="top left")
    fig = _layout(fig, "", 480)
    fig.update_layout(hovermode="x")
    top = float(pct["P95"].max()) * 1.08
    if target:
        top = max(top, target * 1.08)
    fig.update_yaxes(tickformat=",.0f", range=[0, top])
    return fig


def final_histogram(final: np.ndarray, contributed: float, target: float | None = None) -> go.Figure:
    cap = np.percentile(final, 99)
    vals = final[final <= cap]
    fig = go.Figure(go.Histogram(x=vals, nbinsx=60, marker_color=PALETTE[0], marker_line_width=0, opacity=0.85,
                                 hovertemplate="%{x:,.0f}: %{y} paths<extra></extra>"))
    fig.add_vline(x=float(np.median(final)), line=dict(color=INK, width=2),
                  annotation_text="Median", annotation_position="top")
    fig.add_vline(x=contributed, line=dict(color=MUTED, width=1.5, dash="dot"),
                  annotation_text="Contributed", annotation_position="bottom right")
    if target:
        fig.add_vline(x=target, line=dict(color=PALETTE[1], width=1.5), annotation_text="Goal",
                      annotation_position="top right")
    fig = _layout(fig, "", 340, legend=False)
    fig.update_xaxes(tickformat=",.0f")
    fig.update_layout(bargap=0.04)
    return fig
