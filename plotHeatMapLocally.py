# -*- coding: utf-8 -*-
"""
Created on Tue Feb 24 22:02:14 2026

@author: manoj
"""

import requests
import pandas as pd
import plotly.express as px

url = "http://localhost:8000/api/returns"
basePath = 'D:/clickhouse/clickhouse/'
inputDir = basePath + "input/"
nifty100 = pd.read_csv(inputDir + 'ind_nifty100list.csv')
nifty50  = pd.read_csv(inputDir + 'ind_nifty50list.csv')

params = {
    "symbols": ", ".join(f"{s}" for s in nifty50['Symbol'].values),
    "start_date": "2026-02-20",
    "end_date": "2026-02-20"
}


response = requests.get(url, params=params)
data = response.json()["data"]

df = pd.DataFrame(data)

SYMBOL_META_100 = {
    row['Symbol']: {
        "symbol":   row['Symbol'],
        "company":  row.get('Company Name', row['Symbol']),
        "industry": row.get('Industry', row.get('Sector', 'Other'))
    }
    for _, row in nifty100.iterrows()
}
SYMBOL_META_50 = {
    row['Symbol']: {
        "symbol":   row['Symbol'],
        "company":  row.get('Company Name', row['Symbol']),
        "industry": row.get('Industry', row.get('Sector', 'Other'))
    }
    for _, row in nifty50.iterrows()
}

#populate industry values
industry_map = {v["symbol"]: v["industry"] for v in SYMBOL_META_100.values()}
df["industry"] = df["symbol"].map(industry_map)

# Use last date only for snapshot heatmap
latest_date = df["date"].max()
df = df[df["date"] == latest_date]

# If no weights available, assign equal weight
df["weight"] = 1

# Build treemap
fig = px.treemap(
    df,
    path=["industry", "symbol"],
    values="weight",
    color="daily_return",
    color_continuous_scale="RdYlGn",
    color_continuous_midpoint=0
)

fig.update_layout(
    title=f"Market Heatmap - {latest_date}",
    margin=dict(t=50, l=0, r=0, b=0)
)

fig.show()
fig.write_html("industry_heatmap.html")