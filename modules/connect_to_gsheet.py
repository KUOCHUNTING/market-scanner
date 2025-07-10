import os
import json
import base64
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# === ✅ 建立 Google Sheets 連線 ===
def connect_to_gsheet():
    b64_json = os.getenv("GCP_KEY_BASE64")
    if not b64_json:
        raise ValueError("❌ GCP_KEY_BASE64 環境變數未設定")

    info = json.loads(base64.b64decode(b64_json))
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    client = gspread.authorize(creds)
    return client

# === ✅ 寫入出場紀錄至 Google Sheets ===
def write_exit_to_sheet(
    symbol,
    entry_time,
    exit_time,
    return_rate,
    pnl,
    holding_minutes,
    exit_price,
    rsi=None,
    zscore=None,
    roc=None,
    obv=None,
    vwap=None,
    ema5=None,
    ema20=None,
    strategy_name="未知策略"
):
    try:
        # ✅ 開啟 Google Sheets 並選定分頁
        client = connect_to_gsheet()
        sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/14SSmjk2Ae3rqx0VyiVoVWBXpq0NVNvsLs1RWckuX4Ko/edit")
        worksheet = sheet.worksheet("出場紀錄")  # 請確認有這個分頁

        # ✅ 準備寫入資料
        row = [
            symbol,
            entry_time.strftime("%Y-%m-%d %H:%M:%S") if isinstance(entry_time, datetime) else str(entry_time),
            exit_time.strftime("%Y-%m-%d %H:%M:%S") if isinstance(exit_time, datetime) else str(exit_time),
            f"{return_rate:.2f}%",
            f"${pnl:.2f}",
            f"{holding_minutes:.1f}",
            exit_price,
            rsi, zscore, roc, obv, vwap, ema5, ema20,
            strategy_name
        ]

        worksheet.append_row(row, value_input_option="USER_ENTERED")
        print(f"✅ 已寫入出場紀錄：{symbol}")

    except Exception as e:
        print(f"[❌ Google Sheets 寫入失敗] {symbol} ➜ {e}")
