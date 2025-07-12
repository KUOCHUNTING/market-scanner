# === 📦 系統與網路套件 ===
import os
import requests
import warnings
import traceback
import threading
import base64
import random
import time
import json

# === 📊 資料與時間處理 ===
import pandas as pd
from datetime import datetime, timedelta, time as dtime
import pytz

# === 🧾 Google Sheets 套件 ===
import gspread
from google.oauth2.service_account import Credentials
from oauth2client.service_account import ServiceAccountCredentials

# === ✅ 自訂函數：載入股票清單 ===
from .load_stock_list import load_stock_list  # ← 請確保這個檔案存在

# === 🔐 API 金鑰與外部設定 ===
POLYGON_API_KEY = "3Oa52hFieaUvTyToZudJanq39Rw9zApi"
FMP_API_KEY = "RkRQwAwDCPHSTg1QE4MjIwsqWd0iHtd7"
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL",
    "https://discord.com/api/webhooks/1389605152838647909/c2S7EkfYiFBUMF4WWNyk3XrgcsmGA1-8mqXZ19a5vXn-Ti0yY366L3h77SF7M47GOzej")

# === 📁 股票清單檔案路徑 ===
STOCK_LIST_CSV = "filtered_us_stocks_common_only.csv"
stock_list = load_stock_list(STOCK_LIST_CSV)

# === 💰 交易資金管理 ===
TOTAL_CAPITAL = 1_000_000
POSITION_RATIO = 0.05
MAX_CAPITAL_PER_POSITION = 50_000
MAX_SHARES_PER_POSITION = 6000
MAX_ACTIVE_POSITIONS = 10
capital_left = TOTAL_CAPITAL  # 初始資金

# === 🛡️ 出場風控參數 ===
TRAIL_TRIGGER = 0.03            # +3% 啟動移動停利
TRAIL_MARGIN = 0.015            # 回落 1.5% 停利出場
DEFAULT_STOP_LOSS = 0.02        # -2% 強制停損
DEFAULT_TAKE_PROFIT = 0.05      # +5% 預設停利

# === 🕒 建倉時間（美東） ===
eastern = pytz.timezone("US/Eastern")
now_est = datetime.now(eastern)
print("建倉時間（美東）:", now_est.strftime("%Y-%m-%d %H:%M:%S"))

# === 📈 持倉紀錄變數 ===
positions = {}             # ➜ 用於正式記錄持倉，供出場模組使用
entered_positions = {}     # ➜ 防止重複建倉用

