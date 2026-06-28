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
from kiteconnect.exceptions import NetworkException
import re

#Load all utility and inputs required for the below code
load_dotenv()
KITE_API_KEY = os.getenv("KITE_API_KEY")
KITE_API_SECRET = os.getenv("KITE_API_SECRET")
token_obj = os.getenv('token_obj')

confirm = input("Confirm if the request token was already requested in the morning? ")
kite = KiteConnect(api_key=KITE_API_KEY)

def saveToken(token_obj):
    
    with open(".env", "r") as f:
        content = f.read()

    new_content = re.sub(r'token_obj\s*=\s*"[^"]*"', f'token_obj="{token_obj}"', content)
    
    with open(".env","w") as f:
        f.write(new_content)
    
    print('.env file updated with new token values')

if confirm in ['Y','y']:
    token_obj = os.getenv('token_obj')
    kite.set_access_token(token_obj)  # Set the saved token
    try:
        a = kite.profile()
    except:
        print("Access token is expired, most probably didn't saved in the morning, inputting....")
        print(f'https://kite.zerodha.com/connect/login?api_key={KITE_API_KEY}')
        token_obj = input("Enter the access token, hit above URL: ")
        data = kite.generate_session(token_obj, api_secret=KITE_API_SECRET)
        
        token_obj = data['access_token']
        kite.set_access_token(token_obj)
        
        saveToken(token_obj)
        
else:
    
    print(f'https://kite.zerodha.com/connect/login?api_key={KITE_API_KEY}')
    token_obj = input("Enter the request token from URL: ")
    data = kite.generate_session(token_obj, api_secret=KITE_API_SECRET)
        
    token_obj = data['access_token']
    kite.set_access_token(token_obj)
    
    saveToken(token_obj)


basePath = 'D:/clickhouse/clickhouse/'
# basePath = '/home/ubuntu/zz/'
inputDir = basePath + "input/"

symbols = ['NIFTY','SENSEX','BANKNIFTY','FINNIFTY','BANKEX','MIDCNPNIFTY']

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
        #host = 'REDACTED',
        port=os.getenv('port'),
        user=os.getenv('user'),
        password=os.getenv('password')
        #password='***REMOVED***'
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
futInstruments = instruments[instruments['instrument_type'] == 'FUT'].reset_index(drop = True)
optInstruments = instruments[instruments['instrument_type'] .isin(['CE','PE'])].reset_index(drop = True)

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


def safe_fetch(currentInstrument, startDate, endDate, max_retries=5):
    delay = 10
    
    for attempt in range(max_retries):
        try:
            return fetchOptData(
                currentInstrument, 'NSE', 'minute', startDate, endDate
            )
        except NetworkException as e:
            if "Too many requests" in str(e):
                logger.info(f"Rate limit hit for {ticker}. Sleeping {delay}s...")
                time.sleep(delay)
                delay *= 2  # exponential backoff
            else:
                raise e

    raise Exception(f"Max retries exceeded for {ticker}")


def fetchOptData(currentInstrument, exchange, interval, from_date, to_date):
    kite = get_kite_for_user()
    batch_days = kite_interval_day_limit[interval]
    
    from_dt = datetime.strptime(from_date, "%Y-%m-%d")
    to_dt = datetime.strptime(to_date, "%Y-%m-%d")
    days =  (to_dt - from_dt).days + 1

    df = pd.DataFrame()
    
    for i in tqdm(range(0, days, batch_days)):
        from_date = from_dt + timedelta(days=i)
        to_date = min(from_date + timedelta(days = batch_days), to_dt)
        
        data = kite.historical_data(currentInstrument, from_date.strftime("%Y-%m-%d"), to_date.strftime("%Y-%m-%d"), interval, oi = True)
        df = pd.concat([df, pd.DataFrame(data)], axis=0)    
    
    df = df.drop_duplicates().reset_index(drop = True)
    return df



client = get_client()
client.execute("""
CREATE TABLE IF NOT EXISTS mkt.options_1min
(
    exchange LowCardinality(String),
    symbol String,
    instrument_token UInt32,
    expiry Date,
    date Date,
    strike Decimal(10,2),
    optType LowCardinality(String),
    timestamp DateTime,
    open Float64,
    high Float64,
    low Float64,
    close Float64,
    volume UInt64,
    oi UInt64
)
ENGINE = ReplacingMergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (exchange, symbol, expiry, strike, optType, timestamp)
""")

derivCols = ['symbol','instrument_token','exchange','expiry','strike', 'optType', 'timestamp','open','high', 'low', 'close', 'volume','oi','date']


for ticker in symbols:
    
    logger.info(f"Fetching data for instrument {ticker}, start date: {startDate}, end date: {endDate}")
    allInstruments = optInstruments[optInstruments['name'] == ticker].reset_index(drop = True)
    
    for j in range(len(allInstruments)):
        currentInstrument = allInstruments['instrument_token'][j]
        df = safe_fetch(currentInstrument, startDate, endDate)
        
        if df.empty:
            logger.warning(f"No data fetched for instrument {ticker}. Skipping insert.")
            continue
        
        ticker = allInstruments['tradingsymbol'][j]
        logger.info(f"Row number {j}: Data count for instrument {ticker}, count: {len(df)}")
        
        df['exchange'] = 'BSE' if ticker in ['SENSEX','BANKEX'] else 'NSE'
        df['symbol'] = allInstruments['name'][j]
        df['instrument_token'] = currentInstrument
        df['instrument_token'] = df['instrument_token'].astype('uint32')
        df['expiry'] = allInstruments['expiry'][j]
        df['expiry'] = pd.to_datetime(df['expiry']).dt.date
        df['strike'] = allInstruments['strike'][j]
        df['strike'] = df['strike'].astype('str')  # Let ClickHouse parse as Decimal
        df['optType'] = allInstruments['instrument_type'][j]
        df['timestamp'] = (df["date"].dt.tz_localize(None))
        df['date'] = pd.to_datetime(df['timestamp']).dt.date

        df = df[derivCols]
        
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
        INSERT INTO mkt.options_1min
        (symbol, instrument_token, exchange, expiry, strike, optType, timestamp,
         open, high, low, close, volume, oi, date)
        VALUES
        """, data)
        
        logger.info(f"Data saved for instrument {ticker} in clickhouse")
        
        #Check if the data matches with what you are uploading
        db_count = client.execute(f"select count() from mkt.options_1min FINAL where instrument_token='{currentInstrument}' and toDate(timestamp)>=toDate('{startDate}') and toDate(timestamp) <= toDate('{endDate}')")[0][0]
        if len(df) != db_count:
            logger.error(f"Error data length mismatch for {ticker}, python: {len(df)}, clickhouse: {db_count}")
            
        time.sleep(1)
        

