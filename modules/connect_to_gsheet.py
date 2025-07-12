from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import os
import json
import base64

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

def write_entry_to_sheet(
    symbol,
    direction,
    shares,
    entry_capital,
    strategy_name,
    confidence_score,
    capital_left
):
    try:
        client = connect_to_gsheet()
        sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/14SSmjk2Ae3rqx0VyiVoVWBXpq0NVNvsLs1RWckuX4Ko/edit") \
                      .worksheet("建倉紀錄")  # 🔁 依照你設定的分頁名

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        row = [
            now,
            symbol,
            direction,
            shares,
            entry_capital,
            strategy_name,
            confidence_score,
            capital_left
        ]

        sheet.append_row(row)
    except Exception as e:
        print(f"❌ [寫入失敗] {symbol} ➜ {e}")

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
    strategy_name="未標記",
    confidence_score=None
):
    try:
        client = connect_to_gsheet()
        sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/14SSmjk2Ae3rqx0VyiVoVWBXpq0NVNvsLs1RWckuX4Ko/edit") \
                      .worksheet("出場紀錄")  # 🔁 分頁名

        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            symbol,
            entry_time.strftime("%Y-%m-%d %H:%M:%S") if entry_time else "",
            exit_time.strftime("%Y-%m-%d %H:%M:%S") if exit_time else "",
            f"{return_rate:.2%}",
            f"${pnl:.2f}",
            holding_minutes,
            f"${exit_price:.2f}",
            rsi,
            zscore,
            roc,
            obv,
            vwap,
            strategy_name,
            confidence_score
        ]

        sheet.append_row(row)
        print(f"✅【出場寫入成功】{symbol} ➜ 已寫入 Google Sheets 出場紀錄")
    except Exception as e:
        print(f"❌【出場寫入失敗】{symbol} ➜ {e}")
