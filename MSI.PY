import os
import pandas as pd
from datetime import datetime, timedelta
from polygon import RESTClient
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator
from ta.volatility import AverageTrueRange

API_KEY = os.getenv("POLYGON_API_KEY") or "YOUR_API_KEY"

def fetch_5min_data(symbol):
    try:
        client = RESTClient(api_key=API_KEY)
        end = datetime.now()
        start = end - timedelta(minutes=300)

        aggs = client.get_aggs(
            ticker=symbol,
            multiplier=5,
            timespan="minute",
            from_=start.strftime("%Y-%m-%d"),
            to=end.strftime("%Y-%m-%d"),
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

        # æé¤åå±±è°åé
        if 45 <= rsi <= 65:
            return "ç¡è¨èï¼åå±±è°ï¼"

        if rsi < 35 and macd > 0 and price > vwap.iloc[-1] and ema_5 > ema_20 and volume_spike and atr > 0:
            return "æ £å¼å¤é  é²å ´è¨è"

        if rsi > 70 and macd < 0 and price < vwap.iloc[-1] and ema_5 < ema_20 and volume_spike:
            return "æ £å¼ç©ºé  é²å ´è¨è"

        if rsi < 45 and price > vwap.iloc[-1] and volume_spike:
            return "é è ¦ï¼æåºè¨è"

        if rsi > 60 and macd < 0 and price < vwap.iloc[-1]:
            return "é è ¦ï¼è½å¼±è¨è"

        return "ç¡æç¢ºè¨è"
    except:
        return "è³æé¯èª¤"

def scan_all_symbols(symbols):
    results = []
    for symbol in symbols:
        df = fetch_5min_data(symbol)
        if df is not None:
            signal = analyze_signals(df)
            results.append((symbol, signal))
    return results

# ç¯ä¾ææ
example_symbols = ["AAPL", "TSLA", "AMD"]
results = scan_all_symbols(example_symbols)
for symbol, signal in results:
    print(f"{symbol}: {signal}")
