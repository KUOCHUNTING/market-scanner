import difflib  # ✅ 加入模糊比對功能
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
        symbol,
        entry_time,
        exit_time,
        f"{return_rate*100:.2f}%",
        pnl,
        holding_minutes,
        exit_price,
        rsi,
        zscore,
        roc,
        obv,
        vwap,
        ema5,
        ema20,
        strategy_name
    ]

    sheet.append_row(row, value_input_option="USER_ENTERED")
