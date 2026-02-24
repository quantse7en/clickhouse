# -*- coding: utf-8 -*-
"""
Created on Tue Feb 24 21:24:49 2026

@author: manoj
"""

import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import sys, os

from queries import get_returns, get_volatility
import pandas as pd

# ── Nifty symbol list (bring your own sector mapping) ────────────────────────
# Format: { 'SYMBOL': 'SECTOR' }  — load from your CSV

basePath = 'D:/clickhouse/clickhouse/'
nifty100 = pd.read_csv(basePath + 'input/ind_nifty100list.csv')
nifty50 = pd.read_csv(basePath + 'input/ind_nifty50list.csv')

# Expecting columns: 'Symbol', 'Industry' (adjust if different)
SYMBOL_SECTOR = dict(zip(nifty50['Symbol'], nifty50['Industry']))

# ── App layout ────────────────────────────────────────────────────────────────
app = dash.Dash(__name__, title="Market Heatmaps")

app.layout = html.Div(style={"backgroundColor": "#0f0f0f", "minHeight": "100vh", "padding": "20px", "fontFamily": "Arial"}, children=[

    html.H2("📊 Market Heatmaps", style={"color": "#00d4aa", "marginBottom": "20px"}),

    # ── Controls ──────────────────────────────────────────────────────────────
    html.Div(style={"display": "flex", "gap": "16px", "flexWrap": "wrap", "alignItems": "flex-end", "marginBottom": "20px"}, children=[

        html.Div([
            html.Label("Heatmap Type", style={"color": "#aaa", "fontSize": "13px"}),
            dcc.RadioItems(
                id="heatmap-type",
                options=[
                    {"label": " 📈 Returns", "value": "returns"},
                    {"label": " 🌡️ Volatility", "value": "volatility"},
                ],
                value="returns",
                inline=True,
                style={"color": "#eee", "fontSize": "14px"},
                inputStyle={"marginRight": "5px", "marginLeft": "12px"}
            )
        ]),

        html.Div([
            html.Label("Start Date", style={"color": "#aaa", "fontSize": "13px"}),
            dcc.DatePickerSingle(id="start-date", date="2024-01-01",
                style={"backgroundColor": "#1e1e1e"})
        ]),

        html.Div([
            html.Label("End Date", style={"color": "#aaa", "fontSize": "13px"}),
            dcc.DatePickerSingle(id="end-date", date="2024-12-31",
                style={"backgroundColor": "#1e1e1e"})
        ]),

        html.Div([
            html.Label("Symbols (comma-separated, blank = all Nifty100)",
                       style={"color": "#aaa", "fontSize": "13px"}),
            dcc.Input(id="symbols-input", type="text",
                      placeholder="RELIANCE,TCS,INFY,...",
                      style={"backgroundColor": "#1e1e1e", "border": "1px solid #333",
                             "color": "#eee", "padding": "6px 10px",
                             "borderRadius": "6px", "width": "320px"})
        ]),

        html.Button("Load", id="load-btn", n_clicks=0,
            style={"padding": "8px 24px", "backgroundColor": "#00d4aa",
                   "border": "none", "color": "#000", "borderRadius": "6px",
                   "fontWeight": "bold", "cursor": "pointer", "fontSize": "14px",
                   "alignSelf": "flex-end"})
    ]),

    # ── Chart ─────────────────────────────────────────────────────────────────
    dcc.Loading(
        type="circle",
        color="#00d4aa",
        children=dcc.Graph(id="heatmap-chart", style={"height": "75vh"})
    )
])


# ── Callback ──────────────────────────────────────────────────────────────────
@app.callback(
    Output("heatmap-chart", "figure"),
    Input("load-btn", "n_clicks"),
    State("heatmap-type", "value"),
    State("start-date", "date"),
    State("end-date", "date"),
    State("symbols-input", "value"),
    prevent_initial_call=False
)
def update_chart(n_clicks, heatmap_type, start_date, end_date, symbols_raw):
    # Resolve symbols
    if symbols_raw and symbols_raw.strip():
        symbols = [s.strip().upper() for s in symbols_raw.split(",") if s.strip()]
    else:
        symbols = list(SYMBOL_SECTOR.keys())  # all Nifty100

    if heatmap_type == "returns":
        return build_returns_treemap(symbols, start_date, end_date)
    else:
        return build_volatility_heatmap(symbols, start_date, end_date)


# ── Returns Treemap (Finviz-style) ────────────────────────────────────────────
def build_returns_treemap(symbols, start_date, end_date):
    data = get_returns(symbols, start_date, end_date)
    if not data:
        return empty_figure("No data returned")

    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])

    # Aggregate: average daily return across the date range per symbol
    summary = df.groupby("symbol")["daily_return"].mean().reset_index()
    summary.columns = ["symbol", "avg_return"]
    summary["sector"] = summary["symbol"].map(SYMBOL_SECTOR).fillna("Other")

    # Add display label with return %
    summary["label"] = summary["symbol"] + "<br>" + summary["avg_return"].apply(
        lambda x: f"+{x:.2f}%" if x >= 0 else f"{x:.2f}%"
    )

    # Color: red ↔ green diverging, centered at 0
    max_abs = summary["avg_return"].abs().max() or 1

    fig = go.Figure(go.Treemap(
        ids=summary["symbol"],
        labels=summary["label"],
        parents=summary["sector"],
        values=[1] * len(summary),          # equal size; swap for market cap if available
        customdata=summary[["avg_return", "symbol"]],
        hovertemplate="<b>%{customdata[1]}</b><br>Avg Return: %{customdata[0]:.2f}%<extra></extra>",
        marker=dict(
            colors=summary["avg_return"],
            colorscale=[
                [0.0,  "#8b0000"],   # deep red
                [0.35, "#d73027"],   # red
                [0.5,  "#1a1a1a"],   # neutral dark
                [0.65, "#1a9850"],   # green
                [1.0,  "#004d00"],   # deep green
            ],
            cmid=0,
            cmin=-max_abs,
            cmax=max_abs,
            colorbar=dict(
                title="Avg Return (%)",
                tickfont=dict(color="#eee"),
                titlefont=dict(color="#eee")
            )
        ),
        textfont=dict(color="white", size=12),
        tiling=dict(packing="squarify"),
        pathbar=dict(visible=True),
        branchvalues="total"
    ))

    fig.update_layout(
        title=dict(text=f"📈 Returns Heatmap — {start_date} to {end_date}",
                   font=dict(color="#eee")),
        paper_bgcolor="#0f0f0f",
        font=dict(color="#eee"),
        margin=dict(t=50, l=10, r=10, b=10),
        treemapcolorway=["#1a1a1a"]
    )
    return fig


# ── Volatility Grid Heatmap ───────────────────────────────────────────────────
def build_volatility_heatmap(symbols, start_date, end_date):
    data = get_volatility(symbols, start_date, end_date)
    if not data:
        return empty_figure("No data returned")

    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

    pivot = df.pivot(index="symbol", columns="date", values="volatility")

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        colorscale="YlOrRd",
        colorbar=dict(
            title="Volatility (%)",
            tickfont=dict(color="#eee"),
            titlefont=dict(color="#eee")
        ),
        hoverongaps=False,
        hovertemplate="<b>%{y}</b><br>Date: %{x}<br>Volatility: %{z:.2f}%<extra></extra>"
    ))

    fig.update_layout(
        title=dict(text=f"🌡️ Volatility Heatmap — {start_date} to {end_date}",
                   font=dict(color="#eee")),
        paper_bgcolor="#0f0f0f",
        plot_bgcolor="#111",
        font=dict(color="#eee"),
        xaxis=dict(title="Date", tickangle=-45, tickfont=dict(size=9)),
        yaxis=dict(title="Symbol", tickfont=dict(size=10)),
        margin=dict(t=50, l=80, r=20, b=80)
    )
    return fig


def empty_figure(msg):
    fig = go.Figure()
    fig.add_annotation(text=msg, x=0.5, y=0.5, showarrow=False,
                       font=dict(color="#aaa", size=16))
    fig.update_layout(paper_bgcolor="#0f0f0f", plot_bgcolor="#0f0f0f")
    return fig


if __name__ == "__main__":
    app.run(debug=True, port=8050)