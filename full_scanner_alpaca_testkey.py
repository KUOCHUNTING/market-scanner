
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD
from ta.volume import OnBalanceVolumeIndicator
import time

# 讀取 API 金鑰
ALPACA_API_KEY = "PKL93FSW2G20C5XDJU1F"
ALPACA_SECRET_KEY = "x8kQk0ew14LfTGWjv0e7YqFz8sYlV4fWRJtnlzGw"

client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)

def fetch_data_from_alpaca(symbol):
    try:
        now = datetime.now()
        start = now - timedelta(days=5)
        request_params = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Minute,
            start=start,
            end=now,
            adjustment='raw'
        )
        bars = client.get_stock_bars(request_params).df
        df = bars[bars['symbol'] == symbol].copy()
        df.index = pd.to_datetime(df.index)
        df.rename(columns={
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        }, inplace=True)
        return df
    except Exception as e:
        print(f"❌ {symbol} 資料抓取失敗：{str(e)}")
        return None

def calculate_indicators(df):
    try:
        close = df['Close'].to_numpy().ravel()
        volume = df['Volume'].to_numpy().ravel()

        rsi = RSIIndicator(pd.Series(close)).rsi().values.ravel()
        macd = MACD(pd.Series(close)).macd_diff().values.ravel()
        vwap_position = (df['Close'] - df['Close'].rolling(20).mean()).values.ravel()

        return {
            'rsi': rsi[-1],
            'macd': macd[-1],
            'vwap_position': vwap_position[-1],
            'volume_ratio': volume[-1] / (np.mean(volume[-20:]) + 1e-9)
        }
    except Exception as e:
        print(f"❌ 技術指標錯誤：{str(e)}")
        return None

def main():
    stock_list = ["AAPL", "TSLA", "MSFT"]  # 測試用，部署請讀取清單
    print("▶️ 開始使用 Alpaca API 掃描資料（含盤前盤後）")
    for symbol in stock_list:
        print(f"🔍 正在處理：{symbol}")
        df = fetch_data_from_alpaca(symbol)
        if df is None or df.empty or len(df) < 30:
            continue
        indicators = calculate_indicators(df)
        if indicators:
            print(f"✅ {symbol} 指標：RSI={indicators['rsi']:.2f}, MACD={indicators['macd']:.4f}, VWAP乖離={indicators['vwap_position']:.4f}")
        time.sleep(0.8)  # 防止 API 過載

if __name__ == "__main__":
    main()
