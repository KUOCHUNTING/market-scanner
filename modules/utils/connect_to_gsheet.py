import difflib  # ✅ 加入模糊比對功能
import os
import base64
import json
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials
import numpy as np

def to_serializable(value):
    """轉換為 Google Sheets 可接受的 JSON 類型"""
    if isinstance(value, (np.int64, np.int32)):
        return int(value)
    elif isinstance(value, (np.float64, np.float32)):
        return float(value)
    elif isinstance(value, (pd.Timestamp, np.datetime64)):
        return str(value)
    else:
        return value
        
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

    # ✅ 取得所有分頁名稱
    sheet_names = [ws.title for ws in spreadsheet.worksheets()]
    print("📄 現有分頁：", sheet_names)

    # ✅ 模糊比對名稱是否接近
    if sheet_name not in sheet_names:
        close_matches = difflib.get_close_matches(sheet_name, sheet_names, n=3, cutoff=0.6)
        print(f"⚠️ 找不到分頁名稱：'{sheet_name}'")
        if close_matches:
            print(f"🔍 你是不是想找這些？👉 {close_matches}")
        else:
            print("🚫 找不到任何相似分頁名稱，將建立新分頁")

    # ✅ 嘗試載入 / 建立分頁
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows="100", cols="20")
        print(f"🆕 分頁 {sheet_name} 不存在，已自動建立 ✅")

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
        to_serializable(entry_time),
        to_serializable(entry["symbol"]),
        to_serializable(entry["direction"]),
        to_serializable(entry["price"]),
        to_serializable(entry["shares"]),
        to_serializable(entry.get("capital_used", "")),
        to_serializable(entry["strategy_name"]),
        to_serializable(entry.get("confidence_score", "")),
        to_serializable(entry.get("signal_note", "")),
        to_serializable(entry.get("rsi", "")),
        to_serializable(entry.get("zscore", "")),
        to_serializable(entry.get("obv", "")),
        to_serializable(entry.get("vwap", "")),
        to_serializable(entry.get("ema5", "")),
        to_serializable(entry.get("ema20", "")),
        to_serializable(entry.get("bb_upper", "")),
        to_serializable(entry.get("bb_lower", "")),
        to_serializable(entry.get("trend_score", "")),
        to_serializable(entry.get("rrov_score", "")),
        to_serializable(entry.get("mean_score", ""))
    ]

    sheet.append_row(row, value_input_option="USER_ENTERED")

# ✅ 寫入出場記錄
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
    strategy_name=None,
    confidence_score=None
):
    key_base64 = os.getenv("GCP_KEY_BASE64")
    sheet_url = os.getenv("GSHEET_URL")
    if not key_base64 or not sheet_url:
        raise ValueError("❌ GCP_KEY_BASE64 或 GSHEET_URL 未設定")

    sheet = connect_to_gsheet(sheet_url, "出場紀錄", key_base64)

    # 處理時間格式
    if isinstance(entry_time, datetime):
        entry_time = entry_time.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(exit_time, datetime):
        exit_time = exit_time.strftime("%Y-%m-%d %H:%M:%S")

    row = [
        to_serializable(symbol),
        to_serializable(entry_time),
        to_serializable(exit_time),
        to_serializable(f"{return_rate*100:.2f}%"),
        to_serializable(pnl),
        to_serializable(holding_minutes),
        to_serializable(exit_price),
        to_serializable(rsi),
        to_serializable(zscore),
        to_serializable(roc),
        to_serializable(obv),
        to_serializable(vwap),
        to_serializable(ema5),
        to_serializable(ema20),
        to_serializable(strategy_name)
    ]
    sheet.append_row(row, value_input_option="USER_ENTERED")
