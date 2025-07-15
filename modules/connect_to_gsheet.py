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
    return Credentials.from_service_account_info(
        key_dict,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )

# ✅ 連線 Google Sheets（傳入 base64 金鑰與 Sheet URL）
def connect_to_gsheet(sheet_url: str, sheet_name: str, base64_key: str):
    creds = get_credentials_from_base64(base64_key)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(sheet_url).worksheet(sheet_name)
    return sheet

# ✅ 寫入建倉記錄
def write_entry_to_sheet(sheet, symbol, entry_time, entry_price, direction, quantity, strategy_name):
    sheet.append_row([
        symbol,
        entry_time.strftime("%Y-%m-%d %H:%M:%S"),
        "",  # 出場時間
        "",  # 報酬率
        "",  # 損益
        "",  # 持倉時間
        "",  # 出場價
        "", "", "", "", "", "", "",  # 技術指標預留
        strategy_name
    ])

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
