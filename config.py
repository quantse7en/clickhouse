# -*- coding: utf-8 -*-
"""
Created on Fri Feb 20 23:44:46 2026

@author: manoj
"""

from pydantic_settings import BaseSettings

# class Settings(BaseSettings):
#     API_VERSION: str = "v1"
#     ALLOWED_ORIGIN: str
#     OPENAI_API_KEY: str
#     SERPAPI_API_KEY: str
#     MONGO_URL: str
#     MONGO_DB: str
#     SECRET_KEY: str
#     ALGORITHM: str
#     ACCESS_TOKEN_EXPIRE_MINUTES: str = 60
#     KITE_API_KEY: str
#     KITE_API_SECRET: str

#     class Config:
#         env_file = ".env"
#         case_sensitive = True

# settings = Settings()

import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

# Ensure the logs directory exists
os.makedirs("logs", exist_ok=True)

log_file = datetime.now().strftime("logs/trading_bot_%Y-%m-%d.log")

file_handler = RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(module)s.%(funcName)s | %(message)s")
file_handler.setFormatter(formatter)

logger = logging.getLogger("quant-copilot")
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Avoid duplicate logs in Uvicorn/ASGI (optional tweak)
logger.propagate = False