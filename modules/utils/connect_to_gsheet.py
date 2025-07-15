import os
import base64
import json
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials

# ✅ 取得憑證（從 base64 環境變數）
def get_credentials_from_base64(base64_key):
    decoded = base64.b64decode(base64_key)
    key_dict = json.loads(decoded.decode("utf-8"))
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    return Credentials.from_service_account_info(key_dict, scopes=scopes)

# ✅ 連線 Google Sheets（傳入 base64 金鑰與 Sheet URL）
def connect_to_gsheet(sheet_url: str, sheet_name: str, base64_key: str):
    creds = get_credentials_from_base64(base64_key)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(sheet_url).worksheet(sheet_name)
    return sheet

# ✅ 寫入建倉記錄
# modules/connect_to_gsheet.py

def write_entry_to_sheet(entry: dict):
    import gspread
    from google.oauth2.service_account import Credentials
    from datetime import datetime
    import os
    import base64
    import json

    # 取得 Google Sheets 金鑰
    key_base64 = os.getenv("GCP_KEY_BASE64")
    sheet_url = os.getenv("GSHEET_URL")
    decoded = base64.b64decode(key_base64)
    creds_dict = json.loads(decoded.decode("utf-8"))
    creds = Credentials.from_service_account_info(creds_dict)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(sheet_url).worksheet("建倉紀錄")  # ← 替換為你的分頁名稱

    # 準備寫入的資料列
    row = [
        entry["symbol"],
        entry["entry_time"],
        entry["price"],
        entry["direction"],
        entry["shares"],
        entry["strategy_name"],
        entry.get("signal_note", ""),
        entry.get("capital_used", ""),
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
        entry.get("mean_score", ""),
        entry.get("confidence_score", "")
    ]

    # 寫入資料
    sheet.append_row(row, value_input_option="USER_ENTERED")

# ✅ 寫入出場記錄
def write_exit_to_sheet(symbol, entry_time, exit_time, return_rate, pnl, holding_minutes,
                        exit_price, rsi=None, zscore=None, roc=None, obv=None,
                        vwap=None, ema5=None, ema20=None, strategy_name="未標記"):
    from modules.config import GSHEET_URL, GSHEET_KEY_BASE64
    sheet = connect_to_gsheet(GSHEET_URL, "出場記錄", GSHEET_KEY_BASE64)
    sheet.append_row([
        symbol,
        entry_time.strftime("%Y-%m-%d %H:%M:%S"),
        exit_time.strftime("%Y-%m-%d %H:%M:%S"),
        f"{return_rate:.2%}",
        f"{pnl:.2f}",
        holding_minutes,
        f"{exit_price:.2f}",
        f"{rsi:.2f}" if rsi else "",
        f"{zscore:.2f}" if zscore else "",
        f"{roc:.2f}" if roc else "",
        f"{obv:.2f}" if obv else "",
        f"{vwap:.2f}" if vwap else "",
        f"{ema5:.2f}" if ema5 else "",
        f"{ema20:.2f}" if ema20 else "",
        strategy_name
    ])
