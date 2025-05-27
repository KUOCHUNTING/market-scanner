import os
import pandas as pd
from datetime import datetime
from polygon import RESTClient
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator
from ta.volatility import AverageTrueRange

API_KEY = os.getenv("POLYGON_API_KEY") or "YOUR_API_KEY"

def fetch_5min_data(symbol):
    try:
        client = RESTClient(api_key=API_KEY)
        # ✅ 固定為 2025/5/22 的交易日資料（美股）
        from_date = "2025-05-22"
        to_date = "2025-05-22"

        aggs = client.get_aggs(
            ticker=symbol,
            multiplier=5,
            timespan="minute",
            from_=from_date,
            to=to_date,
            limit=100,
            adjusted=True
        )

        bars = aggs.results if hasattr(aggs, "results") else aggs
        if not bars or not isinstance(bars, list) or len(bars) == 0:
            return None

        data = []
        for bar in bars:
            data.append({
                "timestamp": pd.to_datetime(bar["t"], unit="ms"),
                "open": bar["o"],
                "high": bar["h"],
                "low": bar["l"],
                "close": bar["c"],
                "volume": bar["v"]
            })

        df = pd.DataFrame(data)
        df.set_index("timestamp", inplace=True)
        df["vwap"] = (df["close"] * df["volume"]).cumsum() / df["volume"].cumsum()
        return df
    except:
        return None

def analyze_signals(df):
    try:
        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"]
        vwap = df["vwap"]
        price = close.iloc[-1]

        rsi = RSIIndicator(close, window=6).rsi().iloc[-1]
        macd = MACD(close).macd_diff().iloc[-1]
        ema_5 = EMAIndicator(close, window=5).ema_indicator().iloc[-1]
        ema_20 = EMAIndicator(close, window=20).ema_indicator().iloc[-1]
        atr = AverageTrueRange(high=high, low=low, close=close).average_true_range().iloc[-1]

        volume_avg = volume.iloc[-20:].mean()
        volume_now = volume.iloc[-1]
        volume_spike = volume_now > volume_avg * 2

        if 45 <= rsi <= 65:
            return "無訊號（半山腰）"

        if rsi < 35 and macd > 0 and price > vwap.iloc[-1] and ema_5 > ema_20 and volume_spike and atr > 0:
            return "正式多頭進場訊號"

        if rsi > 70 and macd < 0 and price < vwap.iloc[-1] and ema_5 < ema_20 and volume_spike:
            return "正式空頭進場訊號"

        if rsi < 45 and price > vwap.iloc[-1] and volume_spike:
            return "預警：抄底訊號"

        if rsi > 60 and macd < 0 and price < vwap.iloc[-1]:
            return "預警：轉弱訊號"

        return "無明確訊號"
    except:
        return "資料錯誤"

def scan_symbols(symbols):
    results = []
    for symbol in symbols:
        df = fetch_5min_data(symbol)
        if df is not None:
            signal = analyze_signals(df)
            results.append((symbol, signal))
    return results

# 範例執行
symbols = ["AAPL", "TSLA", "AMD"]
results = scan_symbols(symbols)
for symbol, signal in results:
    print(f"{symbol}: {signal}")
