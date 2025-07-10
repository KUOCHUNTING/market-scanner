import os
import pytz
from datetime import datetime
from core import load_stock_list
from ta.momentum import RSIIndicator, ROCIndicator
from ta.volume import OnBalanceVolumeIndicator
from ta.trend import EMAIndicator
from ta.volatility import BollingerBands
import random
import threading
import time
# === 📦 系統與網路套件 ===
import os
import random
import requests
import traceback
# === 📊 資料處理 ===
import pandas as pd
from datetime import datetime
from datetime import datetime, time
from datetime import datetime, timedelta, time as dtime
from datetime import datetime, timedelta
# === 📈 技術指標（ta-lib 套件）===
from ta.momentum import RSIIndicator, ROCIndicator
from ta.volume import OnBalanceVolumeIndicator
from ta.trend import EMAIndicator
from ta.volatility import BollingerBands

# === 📡 Polygon API 套件 ===
from polygon import RESTClient

# === 🧾 Google Sheets 套件 ===
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import base64
import json
import os, json, base64
from google.oauth2.service_account import Credentials
import warnings
# === API & 常數設定 ===
POLYGON_API_KEY = "3Oa52hFieaUvTyToZudJanq39Rw9zApi"
STOCK_LIST_CSV = "filtered_us_stocks_common_only.csv"
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1389605152838647909/c2S7EkfYiFBUMF4WWNyk3XrgcsmGA1-8mqXZ19a5vXn-Ti0yY366L3h77SF7M47GOzej")
FMP_API_KEY = "RkRQwAwDCPHSTg1QE4MjIwsqWd0iHtd7"

# === 交易設定 ===
TOTAL_CAPITAL = 1_000_000
POSITION_RATIO = 0.05
MAX_CAPITAL_PER_POSITION = 50_000
MAX_SHARES_PER_POSITION = 6000
MAX_ACTIVE_POSITIONS = 10

# === 🛡️ 出場風控參數（含三段鎖利）===
TRAIL_TRIGGER = 0.03            # +3% 啟動移動停利
TRAIL_MARGIN = 0.015            # 回落 1.5% 停利出場
DEFAULT_STOP_LOSS = 0.02        # -2% 強制停損
DEFAULT_TAKE_PROFIT = 0.05      # +5% 預設停利

# 在 config.py 裡
STOCK_LIST_CSV = "filtered_us_stocks_common_only.csv"

# 建立美東時間
eastern = pytz.timezone("US/Eastern")
now_est = datetime.now(eastern)
print("建倉時間（美東）:", now_est.strftime("%Y-%m-%d %H:%M:%S"))
