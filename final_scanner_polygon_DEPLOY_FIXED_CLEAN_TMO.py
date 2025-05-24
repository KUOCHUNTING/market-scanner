
# final_scanner_polygon_DEPLOY_FULL_v3.py
import requests
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta

import ta
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD
from ta.volume import VolumeWeightedAveragePrice

def calculate_indicators(df):
    df = df.copy()
    df['RSI'] = RSIIndicator(close=df['c'], window=14).rsi()
    df['%K'] = StochasticOscillator(high=df['h'], low=df['l'], close=df['c'], window=14).stoch()
    df['%D'] = StochasticOscillator(high=df['h'], low=df['l'], close=df['c'], window=14).stoch_signal()
    macd = MACD(close=df['c'])
    df['MACD'] = macd.macd()
    df['MACD_signal'] = macd.macd_signal()
    df['MACD_hist'] = macd.macd_diff()
    df['Volume_Avg'] = df['v'].rolling(window=10).mean()
    df['Volume_Spike'] = df['v'] > df['Volume_Avg'] * 1.5
    vwap = VolumeWeightedAveragePrice(high=df['h'], low=df['l'], close=df['c'], volume=df['v'], window=14)
    df['VWAP'] = vwap.vwap()
    return df

def check_early_alert_long(df):
    return (
        df['RSI'].iloc[-1] > 30 and
        df['%K'].iloc[-1] < 30 and df['%K'].iloc[-1] > df['%D'].iloc[-1] and
        df['MACD_hist'].iloc[-1] > df['MACD_hist'].iloc[-2]
    )

def check_formal_entry_long(df):
    return (
        df['RSI'].iloc[-1] > 50 and
        df['MACD'].iloc[-1] > df['MACD_signal'].iloc[-1] and
        df['MACD_hist'].iloc[-1] > 0 and
        df['c'].iloc[-1] > df['VWAP'].iloc[-1] and
        df['Volume_Spike'].iloc[-1]
    )


import threading

API_KEY = "sRnfK4Nqsa8xTHXC0gBeNE3uh11_Q4ln"

def load_symbols(csv_path="filtered_us_stocks_common_only.csv"):
    try:
        df = pd.read_csv(csv_path)
        return df["symbol"].dropna().unique().tolist()
    except:
        return ["AAPL", "MSFT"]

def fetch_5min_bars(symbol, days=2):
    end = int(datetime.now().timestamp()) * 1000
    start = int((datetime.now() - timedelta(days=days)).timestamp()) * 1000
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/5/minute/{start}/{end}?adjusted=true&sort=desc&limit=1000&apiKey={API_KEY}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json().get("results", [])
            if not data:
                return None
            df = pd.DataFrame(data)
            df["t"] = pd.to_datetime(df["t"], unit="ms")
            df.set_index("t", inplace=True)
            df = df.sort_index()
            df.rename(columns={"c": "close", "h": "high", "l": "low", "o": "open", "v": "volume"}, inplace=True)
            return df[["open", "high", "low", "close", "volume"]]
        else:
            return None
    except:
        return None

def compute_indicators(df):
    df["rsi"] = compute_rsi(df["close"])
    df["macd"], df["macd_signal"] = compute_macd(df["close"])
    df["atr"] = compute_atr(df)
    return df

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / (avg_loss + 1e-6)
    return 100 - (100 / (1 + rs))

def compute_macd(series, short=12, long=26, signal=9):
    short_ema = series.ewm(span=short, adjust=False).mean()
    long_ema = series.ewm(span=long, adjust=False).mean()
    macd = short_ema - long_ema
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    return macd, signal_line

def compute_atr(df, period=14):
    high_low = df["high"] - df["low"]
    high_close = np.abs(df["high"] - df["close"].shift())
    low_close = np.abs(df["low"] - df["close"].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def scan_symbol(symbol):
    df = fetch_5min_bars(symbol)
    if df is None or len(df) < 50:
        return

    df = compute_indicators(df)
    latest = df.iloc[-1]
    rsi, macd_diff, atr = latest["rsi"], latest["macd"] - latest["macd_signal"], latest["atr"]

    if rsi < 30 and macd_diff > 0 and atr > 0.5:
        print(f"✅ [正式進場訊號] {symbol} RSI={rsi:.1f}, MACD差={macd_diff:.2f}, ATR={atr:.2f}")
    elif rsi < 35:
        print(f"🟡 [預警] {symbol} RSI={rsi:.1f}, MACD差={macd_diff:.2f}")
    else:
        print(f"📉 {symbol} 無訊號")

def main():
    print(f"▶️ 啟動全市場掃描（{datetime.now()}）")
    symbols = load_symbols("filtered_us_stocks_common_only.csv")
    threads = []

    for symbol in symbols:
        t = threading.Thread(target=scan_symbol, args=(symbol,))
        threads.append(t)
        t.start()
        time.sleep(0.2)  # 控制頻率避免被限速

    for t in threads:
        t.join()

if __name__ == "__main__":
    main()



def check_early_alert_short(df):
    return (
        df['RSI'].iloc[-1] < 70 and
        df['%K'].iloc[-1] > 70 and df['%K'].iloc[-1] < df['%D'].iloc[-1] and
        df['MACD_hist'].iloc[-1] < df['MACD_hist'].iloc[-2]
    )

def check_formal_entry_short(df):
    return (
        df['RSI'].iloc[-1] < 50 and
        df['MACD'].iloc[-1] < df['MACD_signal'].iloc[-1] and
        df['MACD_hist'].iloc[-1] < 0 and
        df['c'].iloc[-1] < df['VWAP'].iloc[-1] and
        df['Volume_Spike'].iloc[-1]
    )

def classify_signal(df, tick_percentile, trin_value, is_15m_confirmed):
    signal = None
    if check_formal_entry_long(df):
        signal = "正式進場（多）"
    elif check_early_alert_long(df):
        signal = "預警進場（多）"
    elif check_formal_entry_short(df):
        signal = "正式進場（空）"
    elif check_early_alert_short(df):
        signal = "預警進場（空）"

    # 共振條件
    if signal and (
        (signal.endswith("（多）") and tick_percentile > 90 and trin_value < 1 and is_15m_confirmed) or
        (signal.endswith("（空）") and tick_percentile < 10 and trin_value > 1.2 and is_15m_confirmed)
    ):
        signal += "＋共振"

    return signal

def push_to_discord(symbol, signal):
    print(f"[DISCORD] {symbol} 符合條件：{signal}")

def write_to_sheet(symbol, signal, price):
    print(f"[SHEET] 寫入：{symbol}, {signal}, 現價：{price}")



import gspread
from oauth2client.service_account import ServiceAccountCredentials

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1373309204810563604/CUhbQ6sFvtNqSsEXxw7TnnMocMyV_VwfDqr7p3iiz3lXFUkzLNZXbzdO9EEEp87pk6lE"
SHEET_NAME = "交易紀錄總表"
TAB_NAME = "訊號紀錄"

# Sheets 認證（需事先在雲端建立授權 JSON 並掛載到環境變數或本地）
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("gspread_key.json", scope)
sheet_client = gspread.authorize(credentials)
sheet = sheet_client.open(SHEET_NAME).worksheet(TAB_NAME)

def push_to_discord(symbol, signal):
    content = f"**{symbol}** 出現訊號：`{signal}`"
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": content}, timeout=10)
    except Exception as e:
        print(f"[DISCORD 發送錯誤] {e}")

def write_to_sheet(symbol, signal, price):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        sheet.append_row([timestamp, symbol, signal, price])
    except Exception as e:
        print(f"[SHEET 寫入錯誤] {e}")



def scan_all_symbols(symbols, tick_percentile=50, trin_value=1, is_15m_confirmed=True):
    for symbol in symbols:
        print(f"掃描中：{symbol}")
        df = fetch_5min_bars(symbol)
        if df is None or len(df) < 20:
            continue
        df = calculate_indicators(df)
        signal = classify_signal(df, tick_percentile, trin_value, is_15m_confirmed)
        if signal:
            price = df['c'].iloc[-1]
            push_to_discord(symbol, signal)
            write_to_sheet(symbol, signal, price)

def main():
    print("▶️ 啟動主流程...")
    symbols = load_symbols()
    while True:
        print(f"🔁 新一輪掃描開始，共 {len(symbols)} 檔...")
        scan_all_symbols(symbols)
        print("⏳ 等待下一輪掃描 60 秒...")
        time.sleep(60)

if __name__ == "__main__":
    main()



def calculate_tmo(df, short_period=5, long_period=20, signal_period=5):
    close = df['c']
    mom = close.diff()
    tmo_ema_short = mom.ewm(span=short_period, adjust=False).mean()
    tmo_ema_long = mom.ewm(span=long_period, adjust=False).mean()
    tmo = tmo_ema_short - tmo_ema_long
    signal = tmo.ewm(span=signal_period, adjust=False).mean()
    df['TMO'] = tmo
    df['TMO_Signal'] = signal
    return df

# 原有的 calculate_indicators 補入 TMO
def calculate_indicators(df):
    df = df.copy()
    df['RSI'] = RSIIndicator(close=df['c'], window=14).rsi()
    df['%K'] = StochasticOscillator(high=df['h'], low=df['l'], close=df['c'], window=14).stoch()
    df['%D'] = StochasticOscillator(high=df['h'], low=df['l'], close=df['c'], window=14).stoch_signal()
    macd = MACD(close=df['c'])
    df['MACD'] = macd.macd()
    df['MACD_signal'] = macd.macd_signal()
    df['MACD_hist'] = macd.macd_diff()
    df['Volume_Avg'] = df['v'].rolling(window=10).mean()
    df['Volume_Spike'] = df['v'] > df['Volume_Avg'] * 1.5
    vwap = VolumeWeightedAveragePrice(high=df['h'], low=df['l'], close=df['c'], volume=df['v'], window=14)
    df['VWAP'] = vwap.vwap()
    df = calculate_tmo(df)
    return df

def check_formal_entry_long(df):
    return (
        df['RSI'].iloc[-1] > 50 and
        df['MACD'].iloc[-1] > df['MACD_signal'].iloc[-1] and
        df['MACD_hist'].iloc[-1] > 0 and
        df['c'].iloc[-1] > df['VWAP'].iloc[-1] and
        df['Volume_Spike'].iloc[-1] and
        df['TMO'].iloc[-1] > df['TMO_Signal'].iloc[-1]
    )

def check_formal_entry_short(df):
    return (
        df['RSI'].iloc[-1] < 50 and
        df['MACD'].iloc[-1] < df['MACD_signal'].iloc[-1] and
        df['MACD_hist'].iloc[-1] < 0 and
        df['c'].iloc[-1] < df['VWAP'].iloc[-1] and
        df['Volume_Spike'].iloc[-1] and
        df['TMO'].iloc[-1] < df['TMO_Signal'].iloc[-1]
    )
