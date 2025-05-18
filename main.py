import pandas as pd
import yfinance as yf
import requests
import time
import os
from datetime import datetime
import pytz
from concurrent.futures import ThreadPoolExecutor

DISCORD_WEBHOOK = "https://discord.com/api/webhooks/你的網址貼這裡"
positions = {}
test_mode = True  # True = 測試模式，False = 僅盤中運行

def is_market_open():
    eastern = pytz.timezone("US/Eastern")
    now_est = datetime.now(eastern)
    if now_est.weekday() >= 5:
        return False
    market_open = now_est.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now_est.replace(hour=16, minute=0, microsecond=0)
    return market_open <= now_est <= market_close

def get_all_us_symbols():
    url = "https://raw.githubusercontent.com/ldavis44/stock-symbol-list/master/all/all_tickers.txt"
    try:
        r = requests.get(url)
        return [s.strip().replace(".", "-") for s in r.text.splitlines() if s.strip()]
    except:
        return []

def get_tick_data():
    try:
        df = yf.download("^TICK", period="1d", interval="1m", progress=False)
        df.dropna(inplace=True)
        latest = df["Close"].iloc[-1]
        slope = df["Close"].diff().tail(3).mean()
        percentile = (df["Close"] < latest).sum() / len(df["Close"]) * 100
        return latest, slope, percentile
    except:
        return 0, 0, 50

def send_to_discord(message):
    try:
        requests.post(DISCORD_WEBHOOK, json={"content": message})
    except:
        pass

def log_to_excel(symbol, action, price, tick_val, tick_slope, tick_perc):
    today = datetime.now().strftime("%Y%m%d")
    filename = f"signals_{today}.xlsx"
    df_new = pd.DataFrame([{
        "時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "股票代碼": symbol,
        "事件": action,
        "價格": round(price, 2),
        "TICK值": round(tick_val, 1),
        "TICK斜率": round(tick_slope, 1),
        "TICK百分位": round(tick_perc, 1)
    }])
    if os.path.exists(filename):
        df_old = pd.read_excel(filename)
        df_all = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df_all = df_new
    df_all.to_excel(filename, index=False)

def calc_indicators(df):
    df["SMA20"] = df["Close"].rolling(20).mean()
    df["STD"] = df["Close"].rolling(20).std()
    df["Upper"] = df["SMA20"] + 2 * df["STD"]
    df["Lower"] = df["SMA20"] - 2 * df["STD"]
    df["Basis"] = df["SMA20"]
    rsi = df["Close"].rolling(21).apply(lambda x: 100 - (100 / (1 + (x.pct_change().dropna() > 0).sum() / max((x.pct_change().dropna() < 0).sum(), 1))), raw=False)
    tmo = rsi.rolling(5).mean().rolling(3).mean()
    signal = tmo.rolling(3).mean()
    df["TMO"] = tmo
    df["TMO_signal"] = signal
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal_macd = macd.ewm(span=9, adjust=False).mean()
    df["MACD_line"] = macd
    df["MACD_signal"] = signal_macd
    df["MACD_hist"] = macd - signal_macd
    df["TP"] = (df["High"] + df["Low"] + df["Close"]) / 3
    df["Cum_TPV"] = (df["TP"] * df["Volume"]).cumsum()
    df["Cum_Vol"] = df["Volume"].cumsum()
    df["VWAP"] = df["Cum_TPV"] / df["Cum_Vol"]
    df["VolAvg"] = df["Volume"].rolling(16).mean()
    return df
