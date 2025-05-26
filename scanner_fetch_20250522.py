
import os
from datetime import datetime
import pandas as pd
from polygon import RESTClient
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD

API_KEY = os.getenv("POLYGON_API_KEY") or "YmbcjRd1RA6l3pTlN0NvKRzd7OY4eV8k"

def fetch_stock_data(symbol):
    try:
        client = RESTClient(api_key=API_KEY)

        # 固定抓 2025/5/22 收盤前的 35 分鐘（15:25～15:59）
        end = datetime(2025, 5, 22, 15, 59)
        start = end - pd.Timedelta(minutes=35)

        aggs = client.get_aggs(
            ticker=symbol,
            multiplier=5,
            timespan="minute",
            from_=start.strftime("%Y-%m-%d"),
            to=end.strftime("%Y-%m-%d"),
            limit=100
        )

        if not aggs:
            print(f"[警告] 空回傳：{symbol}")
            return None

        data = [{
            "timestamp": pd.to_datetime(bar["t"], unit='ms'),
            "open": bar["o"],
            "high": bar["h"],
            "low": bar["l"],
            "close": bar["c"],
            "volume": bar["v"]
        } for bar in aggs]

        df = pd.DataFrame(data)
        df.set_index("timestamp", inplace=True)
        return df
    except Exception as e:
        print(f"[錯誤] 抓取資料失敗 {symbol}: {e}")
        return None

def analyze_signal(symbol, df):
    try:
        close = df["close"]
        if len(close) < 35:
            return None

        rsi = RSIIndicator(close).rsi().iloc[-1]
        macd = MACD(close).macd_diff().iloc[-1]
        kd = StochasticOscillator(high=df["high"], low=df["low"], close=close)
        k_value = kd.stoch().iloc[-1]
        d_value = kd.stoch_signal().iloc[-1]

        if rsi < 30 and macd > 0 and k_value > d_value:
            return "多頭進場訊號"
        elif rsi > 70 and macd < 0 and k_value < d_value:
            return "空頭進場訊號"
        return None
    except Exception as e:
        print(f"[錯誤] 分析失敗 {symbol}: {e}")
        return None

def main():
    symbols = ["AAPL", "TSLA", "AMZN", "MSFT"]
    for symbol in symbols:
        df = fetch_stock_data(symbol)
        if df is not None:
            signal = analyze_signal(symbol, df)
            print(f"{symbol} 技術指標結果：{signal}")

if __name__ == "__main__":
    main()
