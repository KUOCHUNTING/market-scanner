import pandas as pd
import yfinance as yf
import requests
import time
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import numpy as np

DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1373309204810563604/CUhbQ6sFvtNqSsEXxw7TnnMocMyV_VwfDqr7p3iiz3lXFUkzLNZXbzdO9EEEp87pk6lE"
positions = {}

# === Google Sheets 寫入函式 ===
def write_to_gsheet_tab(stock_code, signal_type, price, win_rate, return_pct, holding_time):
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("/etc/secrets/gcp_cred.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key("14SSmjk2Ae3rqx0VyiVoVWBXpq0NVNvsLs1RWckuX4Ko")
        try:
            worksheet = sheet.worksheet("測試訊號")
        except:
            worksheet = sheet.add_worksheet(title="測試訊號", rows="1000", cols="20")
        worksheet.append_row([now, stock_code, signal_type, price, win_rate, return_pct, holding_time])
        print(f"[寫入成功] {signal_type} 訊號已寫入 Google Sheets")
    except Exception as e:
        print(f"[寫入失敗] Google Sheets 錯誤：{e}")

# === 主程式區塊 ===
if __name__ == "__main__":
    # 測試寫入功能（修正參數數量）
    write_to_gsheet_tab("TEST", "✅ 測試訊號", 100, "0%", "0%", "0分")
    print(f"[測試] {datetime.now()} 已寫入 Google Sheets 測試訊號")