# -*- coding: utf-8 -*-
"""
Created on Fri Feb 20 23:42:53 2026

@author: manoj
"""

from kiteconnect import KiteConnect
from config import logger
from constants import exchange_suffix_map, kite_interval_day_limit 
from datetime import datetime, timedelta
import pandas as pd
import os
from dotenv import load_dotenv
from tqdm import tqdm
from clickhouse_driver import Client
import sys
import time

#Load all utility and inputs required for the below code
load_dotenv()
KITE_API_KEY = os.getenv("KITE_API_KEY")
KITE_API_SECRET = os.getenv("KITE_API_SECRET")
token_obj = os.getenv('token_obj')

basePath = 'D:/clickhouse/clickhouse/'
inputDir = basePath + "input/"

symbols = pd.read_csv(inputDir + 'ind_nifty100list.csv')

if len(sys.argv)!=3:
    print("Wrong arguments given")
    print("Usage: python fetchData.py <startDate> <endDate>")
    sys.exit(1)
    
    
    
startDate = sys.argv[1]
endDate = sys.argv[2]

logger.info(f"Fetching data from {startDate} to {endDate}......")


def get_client():
    return Client(
        host=os.getenv('host'),
        port=os.getenv('port'),
        user=os.getenv('user'),
        password=os.getenv('password')
    )
    
def get_instrument_token():
    
    kite = KiteConnect(api_key=KITE_API_KEY)
    instruments_data = kite.instruments()
    df = pd.DataFrame(instruments_data)
    df['id'] = df['exchange']+":"+df['tradingsymbol']
    df['fetched_at'] = datetime.utcnow()
    df['expiry'] = pd.to_datetime(df['expiry'])
    df['expiry'] = df['expiry'].replace({pd.NaT: None})
    
    df.to_csv(inputDir + "/instruments.csv", index = None)
    return df

instruments = get_instrument_token()
eqInstruments = instruments[instruments['instrument_type'] == 'EQ'].reset_index(drop = True)

def get_kite_for_user():
    try:
        # /kite_collection = db.db["kite_session"]
        
        kite = KiteConnect(api_key=KITE_API_KEY)
        if token_obj:
            kite.set_access_token(token_obj)

        logger.info(f"User kite connected :: {kite}")
        return kite
    except Exception as e:
        logger.error(f"User's Zerodha token not found. Authenticate first :: {str(e)}")
        return None


def fetch_ohlcv_data(symbol, exchange, interval, from_date, to_date):
    kite = get_kite_for_user()
    batch_days = kite_interval_day_limit[interval]
    
    from_dt = datetime.strptime(from_date, "%Y-%m-%d")
    to_dt = datetime.strptime(to_date, "%Y-%m-%d")
    days =  (to_dt - from_dt).days + 1

    df = pd.DataFrame()
    
    instrumentId = eqInstruments[(eqInstruments['exchange'] == exchange) & (eqInstruments['tradingsymbol'] == symbol)]['instrument_token'].values[0]
    if not instrumentId:
        raise Exception("Instrument token not found")
    
    for i in tqdm(range(0, days, batch_days)):
        from_date = from_dt + timedelta(days=i)
        to_date = min(from_date + timedelta(days = batch_days), to_dt)
        
        data = kite.historical_data(instrumentId, from_date.strftime("%Y-%m-%d"), to_date.strftime("%Y-%m-%d"), interval)
        
        df = pd.concat([df, pd.DataFrame(data)], axis=0)    
    
    df = df.drop_duplicates().reset_index(drop = True)
    return df, instrumentId



client = get_client()

equityCols = ['symbol','instrument_token','exchange','timestamp', 'open', 'high', 'low', 'close', 'volume']
for ticker in symbols['Symbol']:
    
    logger.info(f"Fetching data for instrument {ticker}, start date: {startDate}, end date: {endDate}")
    try:
        df, instrumentId = fetch_ohlcv_data(ticker,'NSE','minute',startDate,endDate)
    except:
        print(f"Rate limit hit for {ticker}, retrying...")
        time.sleep(60)
        df, instrumentId = fetch_ohlcv_data(ticker,'NSE','minute',startDate,endDate)

    logger.info(f"Data count for instrument {ticker}, count: {len(df)}")
    
    df['symbol'] = ticker
    df['instrument_token'] = instrumentId
    df['exchange'] = 'NSE'
    df['timestamp'] = (df["date"].dt.tz_localize(None))
    df = df[equityCols]
    
    logger.info(f"Saving data instrument {ticker} in clickhouse")
    
    data = [tuple(x) for x in df.itertuples(index=False, name=None)]
    
    #Check for client connection, if inactive then up it again
    try:
        client.execute("SELECT 1")
    except:
        client = get_client()
        
    #Mirror the database
    client.execute(
    """
    INSERT INTO mkt.equity_1min
    (symbol, instrument_token, exchange, timestamp,
     open, high, low, close, volume)
    VALUES
    """, data)
    
    logger.info(f"Data saved for instrument {ticker} in clickhouse")
    
    #Check if the data matches with what you are uploading
    db_count = client.execute(f"select count() from mkt.equity_1min FINAL where symbol='{ticker}' and toDate(timestamp)>=toDate('{startDate}') and toDate(timestamp) <= toDate('{endDate}')")[0][0]
    if len(df) != db_count:
        logger.error(f"Error data length mismatch for {ticker}, python: {len(df)}, clickhouse: {db_count}")
