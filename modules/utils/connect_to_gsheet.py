import os
import base64
import json
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials


# ✅ 取得憑證（從 base64 環境變數或參數）
def get_credentials_from_base64(base64_key: str):
    decoded = base64.b64decode(base64_key)
    key_dict = json.loads(decoded.decode("utf-8"))
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    return Credentials.from_service_account_info(key_dict, scopes=scopes)

def connect_to_gsheet(sheet_url: str, sheet_name: str, base64_key: str):
    creds = get_credentials_from_base64(base64_key)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_url(sheet_url)
    print("📄 分頁清單：", [ws.title for ws in spreadsheet.worksheets()])

    try:
        worksheet = spreadsheet.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows="100", cols="20")
        print(f"🆕 分頁 {sheet_name} 不存在，已自動建立")
    
    return worksheet

# ✅ 寫入建倉記錄
def write_entry_to_sheet(entry: dict):
    key_base64 = os.getenv("GCP_KEY_BASE64")
    sheet_url = os.getenv("GSHEET_URL")

    if not key_base64 or not sheet_url:
        raise ValueError("❌ 環境變數 GCP_KEY_BASE64 或 GSHEET_URL 未設定")

    sheet = connect_to_gsheet(sheet_url, "建倉記錄", key_base64)

    entry_time = entry["entry_time"]
    if isinstance(entry_time, datetime):
        entry_time = entry_time.strftime("%Y-%m-%d %H:%M:%S")

    row = [
        entry_time,
        entry["symbol"],
        entry["direction"],
        entry["price"],
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

    sheet.append_row(row, value_input_option="USER_ENTERED")

# ✅ 寫入出場記錄
def write_exit_to_sheet(exit: dict):
    key_base64 = os.getenv("GCP_KEY_BASE64")
    sheet_url = os.getenv("GSHEET_URL")

    if not key_base64 or not sheet_url:
        raise ValueError("❌ GCP_KEY_BASE64 或 GSHEET_URL 未設定")

    sheet = connect_to_gsheet(sheet_url, "出場紀錄", key_base64)

    row = [
        exit["symbol"],
        exit["entry_time"],
        exit["exit_time"],
        exit.get("return_pct", ""),
        exit.get("pnl", ""),
        exit.get("holding_time", ""),
        exit.get("exit_price", ""),
        exit.get("rsi", ""),
        exit.get("zscore", ""),
        exit.get("roc", ""),
        exit.get("obv", ""),
        exit.get("vwap", ""),
        exit.get("ema5", ""),
        exit.get("ema20", ""),
        exit.get("strategy_name", "")
    ]

    sheet.append_row(row, value_input_option="USER_ENTERED")
