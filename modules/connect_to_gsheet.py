import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ✅ 設定認證與工作表
def connect_to_gsheet(sheet_url, sheet_name, credentials_path):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, scope)
    gc = gspread.authorize(credentials)
    sheet = gc.open_by_url(sheet_url).worksheet(sheet_name)
    return sheet

# ✅ 寫入建倉記錄
def write_entry_to_sheet(sheet, symbol, entry_time, entry_price, direction, quantity, strategy_name):
    sheet.append_row([
        symbol,
        entry_time.strftime("%Y-%m-%d %H:%M:%S"),
        "",  # 出場時間暫留空
        "",  # 報酬率
        "",  # 損益
        "",  # 持倉時間
        "",  # 出場價
        "", "", "", "", "", "", "",  # 技術指標暫留空
        strategy_name
    ])

# ✅ 寫入出場記錄
def write_exit_to_sheet(symbol, entry_time, exit_time, return_rate, pnl, holding_minutes,
                        exit_price, rsi=None, zscore=None, roc=None, obv=None,
                        vwap=None, ema5=None, ema20=None, strategy_name="未標記"):
    from modules.config import GSHEET_URL, GCP_KEY_PATH
    sheet = connect_to_gsheet(GSHEET_URL, "出場記錄", GCP_KEY_PATH)
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
