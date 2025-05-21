# -*- coding: utf-8 -*-
import pandas as pd
import ta
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator
import yfinance as yf
import requests
import time
import json
from datetime import datetime
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import joblib
import numpy as np
import os
import pickle
from sklearn.ensemble import RandomForestClassifier

DISCORD_WEBHOOK = None  # 保底定義,防止未設定錯誤

# === TICK 三重共振判斷 ===
def get_market_session(now):
    if now.hour < 9 or (now.hour == 9 and now.minute < 30):
        return "盤前"
    elif now.hour >= 16:
        return "盤後"
    else:
        return "盤中"

def check_tick_triple_confluence():
    # 模擬回傳 true 為符合共振(實際邏輯請按需設計)
    return True

# === ML 訓練資料寫入函式 ===
def write_to_ml_training_log(symbol, indicators, signal_type, return_pct, win_flag, holding_time):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("gcp_cred.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key("1D76gQOfYNm_x8Xw5dKOba4sBN6uVwe0Kio0m2H3I1zE").sheet1

        now = datetime.now(pytz.timezone("US/Eastern")).strftime("%Y-%m-%d %H:%M:%S")
        row = [
            now,
            symbol,
            indicators.get("rsi", ""),
            indicators.get("macd", ""),
            indicators.get("vwap_position", ""),
            indicators.get("volume_ratio", ""),
            indicators.get("tmo", ""),
            indicators.get("tick_confluence", ""),
            signal_type,
            return_pct,
            win_flag,
            holding_time
        ]
        sheet.append_row(row)
    except Exception as e:
        print(f'❌ {symbol} 技術指標處理錯誤:{str(e)}')
        print("寫入 ML 訓練資料失敗:", e)

# === 載入 ML 模型並預測勝率 ===
def predict_win_probability(indicators):
    try:
        model_path = "ml_model.pkl"
        if not os.path.exists(model_path):
            print("未找到 ML 模型,略過機器學習過濾")
            return 1.0  # 如果沒有模型,預設都通過

        model = joblib.load(model_path)
        feature_vector = np.array([[
            indicators.get("rsi", 0),
            indicators.get("macd", 0),
            indicators.get("vwap_position", 0),
            indicators.get("volume_ratio", 1),
            indicators.get("tmo", 0),
            1 if indicators.get("tick_confluence") else 0
        ]])
        proba = model.predict_proba(feature_vector)[0][1]
        return proba
    except Exception as e:
        print(f'❌ {indicators.get("symbol", "?")} 技術指標處理錯誤:{str(e)}')
        print("ML 預測錯誤:", e)
        return 1.0  # 如果錯誤,預設都通過

def write_to_gsheet_tab(stock_code, signal_type, price, win_rate, return_pct, holding_time):
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("gcp_cred.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/14SSmjk2Ae3rqx0VyiVoVWBXpq0NVNvsLs1RWckuX4Ko/")
        tab = sheet.worksheet(signal_type)
        tab.append_row([now, stock_code, price, win_rate, return_pct, holding_time])
    except Exception as e:
        print(f"❌ Sheets 寫入錯誤:{e}")

# === Discord 推播函數 ===
def send_discord_alert(message):
    try:
        if DISCORD_WEBHOOK:
            requests.post(DISCORD_WEBHOOK, json={"content": message})
    except Exception as e:
        print(f"⚠️ Discord 發送失敗:{e}")

# === 出場記錄函數 ===
def record_exit(symbol, exit_type, exit_price):
    entry_data = positions.get(symbol)
    if not entry_data:
        return
    entry_price = entry_data["entry"]
    entry_time = entry_data["time"]
    return_pct = round((exit_price - entry_price) / entry_price * 100, 2)
    holding_time = (datetime.now() - entry_time).total_seconds() / 60
    holding_str = f"{round(holding_time, 1)} 分鐘"
    win_rate = "WIN" if return_pct > 0 else "LOSS"
    print(f"⏹️ 出場紀錄 {symbol} | {exit_type} | 報酬 {return_pct}% | 持倉時間 {holding_str}")
    write_to_gsheet_tab(symbol, "正式出場", exit_price, win_rate, return_pct, holding_str)
    send_discord_alert(f"⏹️ 出場 [{symbol}] | {exit_type.upper()} | 報酬:{return_pct}% | 持倉:{holding_str}")
    del positions[symbol]

# === 讀取股票清單 CSV ===
def load_symbols():
    print("📂 嘗試載入股票清單 CSV 檔...")
    try:
        df = pd.read_csv('filtered_us_stocks_common_only.csv')
        if 'symbol' in df.columns:
            return df['symbol'].dropna().tolist()
        else:
            return df.iloc[:, 0].dropna().tolist()
    except Exception as e:
        print(f'⚠️ 載入股票清單錯誤:{e}')
        return []

def calculate_daily_performance():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("gcp_cred.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet("紀錄")
        data = sheet.get_all_records()
        if not data:
            return
        wins = sum(1 for row in data if float(row["報酬率"]) > 0)
        total = len(data)
        avg_return = sum(float(row["報酬率"]) for row in data) / total
        summary = [datetime.now().strftime("%Y-%m-%d"), total, wins, wins/total*100, avg_return]
        try:
            stat_sheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet("每日統計")
        except Exception:
            stat_sheet = client.open_by_key(GOOGLE_SHEET_ID).add_worksheet(title="每日統計", rows="100", cols="10")
            stat_sheet.append_row(["日期", "總筆數", "獲利筆數", "勝率(%)", "平均報酬(%)", "平均持倉時間"], value_input_option="USER_ENTERED")
        try:
            stat_sheet.append_row(summary, value_input_option="USER_ENTERED")
            print("✅ 已寫入每日統計")
        except Exception as e:
            print(f"❌ 統計寫入失敗:{e}")
    except Exception as e:
        print(f"❌ 每日績效計算錯誤:{e}")

def retrain_ml_model():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("gcp_cred.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet("ML訓練資料集")
        data = sheet.get_all_records()
        if len(data) < 100:
            print("資料量不足，無法訓練ML模型")
            return
        df = pd.DataFrame(data)
        features = df.drop(columns=["報酬率", "獲利與否"])
        labels = df["獲利與否"]
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(features, labels)
        with open("ml_model.pkl", "wb") as f:
            pickle.dump(model, f)
        print("✅ ML 模型已重新訓練並儲存")
    except Exception as e:
        print(f"❌ ML 模型訓練錯誤:{e}")

# === 資金控管設定 ===
capital = 100000  # 本金 10 萬
position_size_pct = 0.05  # 每筆投入 5%
max_stocks_held = 5
positions = {}  # 持倉紀錄:{symbol: {'entry': 價格, 'time': 時間}}

# === 判斷是否出場(停利/停損) ===
def check_exit_conditions(symbol, current_price):
    if symbol not in positions:
        return None
    entry = positions[symbol]['entry']
    gain = (current_price - entry) / entry * 100
    if gain >= 5:
        return 'take_profit'
    elif gain <= -2:
        return 'stop_loss'
    return None

def main():
    global scan_round
    scan_round = 1
    print("▶️ 啟動主流程...")
    symbols = load_symbols()
    print(f"✅ 共載入 {len(symbols)} 檔股票")
    print("開始掃描中...")
    print(f"🔁 開始第 {scan_round} 輪掃描,共 {len(symbols)} 檔股票...")
    start_time = time.time()
    for idx, symbol in enumerate(symbols):
        print(f"🔍 正在掃描第 {idx + 1} 檔股票:{symbol}")
        try:
            data = yf.download(symbol, period="5d", interval="5m", prepost=True)
            if len(data) < 20:
                continue

            # === 技術指標計算 ===
            data["returns"] = data["Close"].pct_change()
            data["rsi"] = RSIIndicator(close=data["Close"], window=14).rsi()
            data["vol_avg"] = data["Volume"].rolling(window=20).mean()
            data["vol_spike"] = data["Volume"] > data["vol_avg"] * 2

            latest = data.iloc[-1]
            price_change_pct = (latest["Close"] - data["Close"].iloc[-6]) / data["Close"].iloc[-6] * 100
            rsi_val = latest["rsi"]
            is_vol_spike = latest["vol_spike"]

            # === 判斷訊號條件 ===
            if price_change_pct > 3 and rsi_val > 70 and is_vol_spike:
                print(f"🚀 訊號成立:{symbol} 價格漲幅 + RSI + 放量 共振")

        except Exception as e:
            print(f'❌ {symbol} 技術指標處理錯誤:{str(e)}')
            print(f"❌ {symbol} 資料抓取失敗:", e)
    print("✅ 本輪掃描結束")

if __name__ == "__main__":
    while True:
        main()
        time.sleep(30)