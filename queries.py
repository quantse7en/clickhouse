# -*- coding: utf-8 -*-
"""
Created on Tue Feb 24 20:16:14 2026

@author: manoj
"""

from clickhouse_driver import Client
import os
from dotenv import load_dotenv
import pandas as pd

basePath = 'D:/clickhouse/clickhouse/'
inputDir = basePath + "input/"

nifty100 = pd.read_csv(inputDir + 'ind_nifty100list.csv')
nifty50 = pd.read_csv(inputDir + 'ind_nifty50list.csv')
load_dotenv()

def get_client():
    return Client(
        host=os.getenv('host'),
        port=os.getenv('port'),
        user=os.getenv('user'),
        password=os.getenv('password')
    )

client = get_client()

SYMBOL_META_100 = {
    row['Symbol']: {
        "symbol":   row['Symbol'],
        "company":  row.get('Company Name', row['Symbol']),
        "sector":   row.get('Sector', 'Other'),
        "industry": row.get('Industry', row.get('Sector', 'Other'))
    }
    for _, row in nifty100.iterrows()
}
SYMBOL_META_50 = {
    row['Symbol']: {
        "symbol":   row['Symbol'],
        "company":  row.get('Company Name', row['Symbol']),
        "sector":   row.get('Sector', 'Other'),
        "industry": row.get('Industry', row.get('Sector', 'Other'))
    }
    for _, row in nifty50.iterrows()
}

def get_returns(symbols, start_date: str, end_date: str):
    client = get_client()
    
    symbols_str = ", ".join(f"'{s}'" for s in symbols)
    query = f"""
        SELECT
            symbol, toDate(timestamp) AS date,
            argMin(close, timestamp) AS open_price,
            argMax(close, timestamp) AS close_price,
            round(
                (argMax(close, timestamp) - argMin(close, timestamp))
                / argMin(close, timestamp) * 100, 2
            ) AS daily_return
        FROM mkt.equity_1min FINAL
        WHERE symbol IN ({symbols_str})
          AND toDate(timestamp) >= toDate('{start_date}')
          AND toDate(timestamp) <= toDate('{end_date}')
        GROUP BY symbol, date
        ORDER BY symbol, date
    """
    rows, cols_meta = client.execute(query, with_column_types=True)
    cols = [c[0] for c in cols_meta]
    return [dict(zip(cols, row)) for row in rows]


def get_volatility(symbols, start_date: str, end_date: str):
    client = get_client()
    
    symbols_str = ", ".join(f"'{s}'" for s in symbols)
    query = f"""
        SELECT
            symbol,
            toDate(timestamp) AS date,
            round(stddevPop(close) / avg(close) * 100, 2) AS volatility
        FROM mkt.equity_1min FINAL
        WHERE symbol IN ({symbols_str})
          AND toDate(timestamp) >= toDate('{start_date}')
          AND toDate(timestamp) <= toDate('{end_date}')
        GROUP BY symbol, date
        ORDER BY symbol, date
    """
    rows, cols_meta = client.execute(query, with_column_types=True)
    cols = [c[0] for c in cols_meta]
    return [dict(zip(cols, row)) for row in rows]

