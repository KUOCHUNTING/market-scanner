# modules/write_entry_to_sheet.py

import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os
import json
import base64

def connect_to_gsheet():
    b64_json = os.getenv("GCP_KEY_BASE64")
    if not b64_json:
        raise ValueError("❌ GCP_KEY_BASE64 環境變數未設定")

    info = json.loads(base64.b64decode(b64_json))
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    client = gspread.authorize(creds)
    return client

def write_entry_to_sheet(symbol, direction, shares, entry_capital, strategy_name, confidence_score, capital_left):
    client = connect_to_gsheet()
    sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/14SSmjk2Ae3rqx0VylVoWBXpq0NVNsLs1RWkdUxX4Ko/edit")
    worksheet = sheet.worksheet("建倉記錄")

    entry_time = datetime.now()
    entry_price = round(entry_capital / shares, 2) if shares > 0 else 0.0

    worksheet.append_row([
        entry_time.strftime("%H:%M"),        # 建倉時間（A）
        entry_time.strftime("%Y-%m-%d"),     # 建倉日期（B）
        symbol,                              # 股票代號（C）
        direction,                           # 方向（D）
        shares,                              # 股數（E）
        entry_capital,                       # 投入資金（F）
        entry_price,                         # 建倉價格（G）
        strategy_name,                       # 策略名稱（H）
        confidence_score,                    # 信心分數（I）
        capital_left                         # 剩餘資金（J）
    ])
