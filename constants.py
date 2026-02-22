# -*- coding: utf-8 -*-
"""
Created on Sun Feb 22 07:44:28 2026

@author: manoj
"""

exchange_suffix_map = {
    "NSE": ".NS",
    "BSE": ".BO",
    "MCX": ".MCX",
}

kite_interval_day_limit = {
    "minute": 30,
    "hour": 400,
    "day": 2000,
    "3minute": 90,
    "5minute": 90,
    "10minute": 90,
    "15minute": 180,
    "30minute": 180,
    "60minute": 400,
}

intervals = {
    "s":1,
    "30s":30,
    "m": 60,
    "3m": 3*60,
    "5m": 5*60,
    "10m": 10*60,
    "15m": 15*60,
    "30m": 30*60,
    "h": 60*60,
    "4h": 4*60*60,
    "d": 24*60*60,
    "w": 5*24*60*60,
    "mo": 21*24*60*60
}