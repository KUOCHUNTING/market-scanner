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
                      .worksheet("建倉紀錄")

        # 🧠 自動延展行數（避免顯示「新增 1000」）
        if sheet.row_count <= len(sheet.get_all_values()):
            sheet.resize(rows=sheet.row_count + 100)

        now = datetime.now()
        row = [
            now.strftime("%Y-%m-%d %H:%M:%S"),   # 建倉時間
            now.strftime("%Y-%m-%d"),            # 建倉日期
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
    holding_time_str,
    exit_price,
    rsi=None,
    zscore=None,
    roc=None,
    obv=None,
    vwap=None,
    ema5=None,
    ema20=None,
    strategy_name="未標記策略"
):
    try:
        client = connect_to_gsheet()
        sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/14SSmjk2Ae3rqx0VyiVoVWBXpq0NVNvsLs1RWckuX4Ko/edit") \
                      .worksheet("出場紀錄")

        # === 🧾 排序與欄位依序如下 ===
        row = [
            symbol,                                        # 1. 股票代號
            entry_time.strftime("%Y-%m-%d %H:%M:%S"),      # 2. 進場時間
            exit_time.strftime("%Y-%m-%d %H:%M:%S"),       # 3. 出場時間
            round(return_rate, 2),                         # 4. 報酬率 (%)
            round(pnl, 2),                                 # 5. 損益 ($)
            holding_time_str,                              # 6. 持倉時間（格式：0:31:00）
            round(exit_price, 2),                          # 7. 出場價 ($)
            round(rsi, 2) if rsi is not None else "",      # 8. RSI
            round(zscore, 2) if zscore is not None else "",# 9. Z-score
            round(roc, 2) if roc is not None else "",      # 10. ROC
            round(obv, 2) if obv is not None else "",      # 11. OBV
            round(vwap, 2) if vwap is not None else "",    # 12. VWAP
            round(ema5, 2) if ema5 is not None else "",    # 13. EMA5
            round(ema20, 2) if ema20 is not None else "",  # 14. EMA20
            strategy_name                                  # 15. 策略名稱
        ]

        sheet.append_row(row, value_input_option="USER_ENTERED")
        print(f"✅【出場寫入成功】{symbol} ➜ 已寫入 Google Sheets 出場紀錄")

    except Exception as e:
        print(f"❌【出場寫入失敗】{symbol} ➜ {e}")
