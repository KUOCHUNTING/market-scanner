import os
import time
import pandas as pd
from datetime import datetime, timedelta
from polygon import RESTClient
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD

API_KEY = os.getenv("POLYGON_API_KEY") or "YOUR_API_KEY"
SCAN_INTERVAL = 60

def fetch_stock_data(symbol):
    try:
        client = RESTClient(api_key=API_KEY)
        end = datetime.now()
        start = end - timedelta(minutes=35)

        aggs = client.get_aggs(
            ticker=symbol,
            multiplier=5,
            timespan="minute",
            from_=start.strftime("%Y-%m-%d"),
            to=end.strftime("%Y-%m-%d"),
            limit=100,
            adjusted=True
        )

        bars = None
        if hasattr(aggs, 'results'):
            bars = aggs.results
        elif isinstance(aggs, list):
            bars = aggs
        else:
            print(f"[WARNING] 未知格式（非 results 或 list）：{symbol}")
            return None

        if not bars or not isinstance(bars, list) or len(bars) == 0:
            print(f"[SKIP] 空資料或格式錯誤：{symbol}")
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
        return df

    except Exception as e:
        print(f"[ERROR] 抓取失敗 {symbol}：{e}")
        return None

print("[INFO] 主程式載入完成，可用 fetch_stock_data('AAPL') 測試")
