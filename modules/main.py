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
warnings.filterwarnings("ignore", category=DeprecationWarning)

# ✅ 定時檢查持倉（每 60 秒觸發一次）
import threading
from datetime import datetime

# 初始化今日清單
symbol_list = load_stock_list()

entered_positions = {}  # ✅ 用來記錄哪些股票已建倉，避免重複