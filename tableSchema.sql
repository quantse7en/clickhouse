--clickHouse files

--Save Equity data from df from KITE API python functions

CREATE TABLE mkt.equity_1min
(
    symbol String,
    instrument_token UInt32,
    exchange LowCardinality(String),
    timestamp DateTime,
    open Float64,
    high Float64,
    low Float64,
    close Float64,
    volume UInt64
)
ENGINE = ReplacingMergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (symbol, timestamp);


--Save Futures data from df from KITE API python functions
CREATE TABLE mkt.futures_1min
(
    symbol String,
    instrument_token UInt32,
    expiry Date,
    timestamp DateTime,
    open Float64,
    high Float64,
    low Float64,
    close Float64,
    volume UInt64,
    oi UInt64
)
ENGINE = ReplacingMergeTree()
PARTITION BY (toYYYYMM(timestamp), expiry)
ORDER BY (symbol, expiry, timestamp);


--Save Options data from df from KITE API python functions
CREATE TABLE mkt.options_1min
(
    exchange LowCardinality(String),
	symbol String,
    instrument_token UInt32,
    expiry Date,
    strike Decimal(10,2),
    optType LowCardinality(String), -- CE / PE
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
ORDER BY (exchange, symbol, expiry, strike, optType, timestamp);
