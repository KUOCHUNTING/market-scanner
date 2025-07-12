import os
import json
import base64
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials

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

# === ✅ 建倉紀錄：快速打包 entry 字典用（推薦）===
def build_entry_record(symbol, direction, shares, capital_used, price, strategy_name):
    now = datetime.now()
    return {
        "建倉時間": now.strftime("%Y-%m-%d %H:%M:%S"),
        "建倉日期": now.strftime("%Y-%m-%d"),
        "股票代號": symbol,
        "方向": direction,
        "股數": shares,
        "投入資金": round(capital_used, 2),
        "建倉價格": round(price, 2),
        "策略名稱": strategy_name
    }

# === ✅ 寫入建倉紀錄至 Google Sheets ===
def write_entry_to_sheet(entry):
    try:
        client = connect_to_gsheet()
        sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/14SSmjk2Ae3rqx0VyiVoVWBXpq0NVNvsLs1RWckuX4Ko/edit")
        worksheet = sheet.worksheet("建倉紀錄")  # 請確保表單中有這分頁

        row = [
            entry.get("建倉時間", ""),
            entry.get("建倉日期", ""),
            entry.get("股票代號", ""),
            entry.get("方向", ""),
            entry.get("股數", ""),
            entry.get("投入資金", ""),
            entry.get("建倉價格", ""),
            entry.get("策略名稱", "")
        ]

        worksheet.append_row(row, value_input_option="USER_ENTERED")
        print(f"✅ 已寫入建倉紀錄：{entry['股票代號']}")

    except Exception as e:
        print(f"[❌ 建倉紀錄寫入失敗] {entry.get('股票代號', '未知')} ➜ {e}")

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
        client = connect_to_gsheet()
        sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/14SSmjk2Ae3rqx0VyiVoVWBXpq0NVNvsLs1RWckuX4Ko/edit")
        worksheet = sheet.worksheet("出場紀錄")

        row = [
            symbol,
            entry_time.strftime("%Y-%m-%d %H:%M:%S") if isinstance(entry_time, datetime) else str(entry_time),
            exit_time.strftime("%Y-%m-%d %H:%M:%S") if isinstance(exit_time, datetime) else str(exit_time),
            f"{return_rate:.2f}%",
            f"${pnl:.2f}",
            f"{holding_minutes:.1f}",
            round(exit_price, 2),
            rsi, zscore, roc, obv, vwap, ema5, ema20,
            strategy_name
        ]

        worksheet.append_row(row, value_input_option="USER_ENTERED")
        print(f"✅ 已寫入出場紀錄：{symbol}")

    except Exception as e:
        print(f"[❌ 出場紀錄寫入失敗] {symbol} ➜ {e}")
