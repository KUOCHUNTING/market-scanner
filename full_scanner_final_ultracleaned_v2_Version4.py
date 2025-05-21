import pandas as pd
import ta
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator
import yfinance as yf
import requests
import time
from datetime import datetime
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import joblib
import numpy as np
import os
import pickle
from sklearn.ensemble import RandomForestClassifier

DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1373309204810563604/CUhbQ6sFvtNqSsEXxw7TnnMocMyV_VwfDqr7p3iiz3lXFUkzLNZXbzdO9EEEp87pk6lE"
GOOGLE_SHEET_ID = "YOUR_GOOGLE_SHEET_ID"  # 請補上你的 Google Sheet ID

# === ML 訓練資料寫入函式 ===
def write_to_ml_training_log(symbol, indicators, signal_type, return_pct, win_flag, holding_time):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("gcp_cred.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1

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
            return 1.0

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
        print(f'❌ 技術指標處理錯誤:{str(e)}')
        print("ML 預測錯誤:", e)
        return 1.0

def write_to_gsheet_tab(stock_code, signal_type, price, win_rate, return_pct, holding_time):
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("gcp_cred.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/")  # 請補上
        tab = sheet.worksheet(signal_type)
        tab.append_row([now, stock_code, price, win_rate, return_pct, holding_time])
    except Exception as e:
        print(f"❌ Sheets 寫入錯誤:{e}")

def send_discord_alert(message):
    try:
        if DISCORD_WEBHOOK:
            requests.post(DISCORD_WEBHOOK, json={"content": message})
    except Exception as e:
        print(f"⚠️ Discord 發送失敗:{e}")

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

capital = 100000
position_size_pct = 0.05
max_stocks_held = 5
positions = {}

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

def get_market_session():
    eastern = pytz.timezone("US/Eastern")
    now_et = datetime.now(eastern).time()
    if now_et >= datetime.strptime("04:00", "%H:%M").time() and now_et < datetime.strptime("09:30", "%H:%M").time():
        return "pre"
    elif now_et >= datetime.strptime("09:30", "%H:%M").time() and now_et < datetime.strptime("16:00", "%H:%M").time():
        return "regular"
    elif now_et >= datetime.strptime("16:00", "%H:%M").time() and now_et < datetime.strptime("20:00", "%H:%M").time():
        return "post"
    else:
        return "closed"

def detect_15min_entry(symbol):
    try:
        df = yf.download(tickers=symbol, interval='15m', period='2d', progress=False, prepost=True)
        if df is None or df.empty:
            print(f'❌ {symbol}:無法從 yfinance 取得資料')
            return False
        if 'Close' not in df.columns or df['Close'].isnull().all():
            print(f'⚠️ {symbol}:缺少 Close 欄位或全部為空')
            return False
        if df is None or df.empty or len(df) < 10:
            return False
        close = df["Close"]
        volume = df["Volume"]
        rsi = RSIIndicator(close=close, window=14).rsi()
        macd = MACD(close=close, window_slow=26, window_fast=12, window_sign=9)
        macd_line = macd.macd()
        macd_signal = macd.macd_signal()
        # 下方 vwma, tmo 需確認已正確定義，如無請註解或自定義
        # ema = EMAIndicator(close=close.diff(), window=5).ema_indicator()
        # conds = [
        #     rsi.iloc[-1] > 50,
        #     macd_line.iloc[-2] < macd_signal.iloc[-2] and macd_line.iloc[-1] > macd_signal.iloc[-1],
        #     close.iloc[-1] > vwma.iloc[-1],
        #     tmo.iloc[-1] > 0 and tmo.iloc[-2] <= 0,
        #     volume.iloc[-1] > volume.rolling(20).mean().iloc[-1] * 1.2
        # ]
        # return sum(conds) >= 3
        # 範例: RSI大於50作為進場
        return rsi.iloc[-1] > 50
    except Exception as e:
        print(f'❌ {symbol} 技術指標處理錯誤:{str(e)}')
        return False

def main():
    print("▶️ 啟動主流程...")
    symbols = load_symbols()
    print(f"✅ 共載入 {len(symbols)} 檔股票")
    print("開始掃描中...")

    start_time = time.time()
    for idx, symbol in enumerate(symbols):
        print(f"🔍 正在掃描第 {idx + 1} 檔股票:{symbol}")
        try:
            data = yf.download(symbol, period="5d", interval="5m", prepost=True)
            if len(data) < 20:
                continue

            # 修正：保證傳入技術指標的都是 1D Series
            close = data["Close"]
            volume = data["Volume"]

            data["returns"] = close.pct_change()
            data["rsi"] = RSIIndicator(close=close, window=14).rsi()
            data["vol_avg"] = volume.rolling(window=20).mean()
            data["vol_spike"] = volume > data["vol_avg"] * 2

            latest = data.iloc[-1]
            price_change_pct = (latest["Close"] - data["Close"].iloc[-6]) / data["Close"].iloc[-6] * 100
            rsi_val = latest["rsi"]
            is_vol_spike = latest["vol_spike"]

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
