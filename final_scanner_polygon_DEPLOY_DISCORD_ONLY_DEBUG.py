
import requests
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD
from ta.volume import VolumeWeightedAveragePrice
# ===== 設定區 =====
API_KEY = "
sRnfK4Nqsa8xTHXC0gBeNE3uh11_Q4ln"
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1373309204810563604/CUhbQ6sFvtNqSsEXxw7TnnMocMyV_VwfDqr7p3iiz3lXFUkzLNZXbzdO9EEEp87pk6lE"
SHEET_NAME = "交易紀錄總表"
TAB_NAME = "訊號紀錄"
CSV_FILE = "filtered_us_stocks_common_only.csv"

def load_symbols():
    df = pd.read_csv(CSV_FILE)
    return df["symbol"].dropna().unique().tolist()

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
            df = df.sort_values("t")
            df.rename(columns={"o": "o", "h": "h", "l": "l", "c": "c", "v": "v"}, inplace=True)
            return df
    except Exception as e:
        print(f"資料抓取錯誤：{symbol} - {e}")
    return None

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

def calculate_indicators(df):
    df['RSI'] = RSIIndicator(close=df['c'], window=14).rsi()
    df['%K'] = StochasticOscillator(high=df['h'], low=df['l'], close=df['c']).stoch()
    df['%D'] = StochasticOscillator(high=df['h'], low=df['l'], close=df['c']).stoch_signal()
    macd = MACD(close=df['c'])
    df['MACD'] = macd.macd()
    df['MACD_signal'] = macd.macd_signal()
    df['MACD_hist'] = macd.macd_diff()
    df['VWAP'] = VolumeWeightedAveragePrice(df['h'], df['l'], df['c'], df['v']).vwap()
    df['Volume_Spike'] = df['v'] > df['v'].rolling(window=10).mean() * 1.5
    df = calculate_tmo(df)
    return df

def classify_signal(df):
    rsi = df['RSI'].iloc[-1]
    macd = df['MACD'].iloc[-1]
    macd_sig = df['MACD_signal'].iloc[-1]
    vw = df['VWAP'].iloc[-1]
    close = df['c'].iloc[-1]
    tmo = df['TMO'].iloc[-1]
    tmo_sig = df['TMO_Signal'].iloc[-1]
    vol = df['Volume_Spike'].iloc[-1]

    if rsi > 50 and macd > macd_sig and close > vw and vol and tmo > tmo_sig:
        return "正式進場（多）"
    if rsi < 50 and macd < macd_sig and close < vw and vol and tmo < tmo_sig:
        return "正式進場（空）"
    if rsi > 30 and tmo > tmo_sig and macd > macd_sig:
        return "預警進場（多）"
    if rsi < 70 and tmo < tmo_sig and macd < macd_sig:
        return "預警進場（空）"
    return None

def push_to_discord(symbol, signal):
    content = f"**{symbol}** 出現訊號：`{signal}`"
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": content}, timeout=10)
    except Exception as e:
        print(f"[DISCORD 發送錯誤] {e}")

def scan_all_symbols():
    # 已上移至 main()
        for idx, symbol in enumerate(symbols):
        print(f'🔍 正在掃描第 {idx+1} 檔：{symbol}')
        df = fetch_5min_bars(symbol)
        if df is None or len(df) < 20:
            continue
        df = calculate_indicators(df)
        signal = classify_signal(df)
        if signal:
            price = df['c'].iloc[-1]
            push_to_discord(symbol, signal)
            # 已移除 Sheets 寫入


def main():
    print(f"▶️ 掃描器啟動成功 | 時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    # 已上移至 main()
    print(f"✅ 股票清單載入成功，共 {len(symbols)} 檔")
    
    print("▶️ 啟動強化版掃描器...")
    while True:
        print(f"🔁 新一輪掃描開始於 {datetime.now().strftime('%H:%M:%S')}...")
        scan_all_symbols()
        print(f"⏳ 等待 60 秒...（下一輪將於 {datetime.now() + timedelta(seconds=60):%H:%M:%S} 執行）")
        time.sleep(60)

if __name__ == "__main__":
    main()
