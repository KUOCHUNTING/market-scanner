# modules/connect_to_gsheet.py
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import os
import base64
import json
import gspread
from google.oauth2.service_account import Credentials

def get_credentials_from_base64(base64_key: str):
    key_data = base64.b64decode(base64_key).decode("utf-8")
    key_dict = json.loads(key_data)
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    return Credentials.from_service_account_info(key_dict, scopes=scopes)

def connect_to_gsheet(sheet_url: str, sheet_name: str, base64_key: str):
    creds = get_credentials_from_base64(base64_key)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(sheet_url).worksheet(sheet_name)
    return sheet

def write_resonance_to_sheet(timestamp, etf, sector_ch, stock_list, sheet_url, sheet_name, base64_key):
    sheet = connect_to_gsheet(sheet_url, sheet_name, base64_key)
    sheet.append_row([timestamp, etf, sector_ch, ", ".join(stock_list)])

def write_entry_to_sheet(entry: dict):
    import base64, os, json
    import gspread
    from google.oauth2.service_account import Credentials
    from datetime import datetime

    # ✅ 把所有 datetime 類型轉成字串，避免寫入失敗
    for key in entry:
        if isinstance(entry[key], datetime):
            entry[key] = entry[key].strftime("%Y-%m-%d %H:%M:%S")

    base64_key = os.getenv("GCP_KEY_BASE64")
    sheet_url = os.getenv("GSHEET_URL")

    if not base64_key or not sheet_url:
        print("❌ GCP_KEY_BASE64 或 GSHEET_URL 未設定")
        return

    # ✅ 解碼金鑰並授權
    key_dict = json.loads(base64.b64decode(base64_key).decode("utf-8"))
    creds = Credentials.from_service_account_info(
        key_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_url(sheet_url).worksheet("建倉記錄")

    # ✅ 統一將所有 datetime 類型轉為字串（避免 JSON 序列化錯誤）
    for key, value in entry.items():
        if isinstance(value, datetime):
            print(f"⚠️ {key} 是 datetime，已轉為字串")
            entry[key] = value.strftime("%Y-%m-%d %H:%M:%S")

    # ✅ 組成寫入的行
    row = [
        entry.get("entry_time", ""),
        entry["symbol"],
        entry["direction"],
        entry["entry_price"],
        entry["shares"],
        entry.get("capital_used", ""),
        entry["strategy_name"],
        entry.get("confidence_score", ""),
        entry.get("signal_note", ""),
        entry.get("rsi", ""),
        entry.get("zscore", ""),
        entry.get("obv", ""),
        entry.get("vwap", ""),
        entry.get("ema5", ""),
        entry.get("ema20", ""),
        entry.get("bb_upper", ""),
        entry.get("bb_lower", ""),
        entry.get("trend_score", ""),
        entry.get("rrov_score", ""),
        entry.get("mean_score", "")
    ]

    # ✅ 寫入 Google Sheets
    sheet.append_row(row, value_input_option="USER_ENTERED")
