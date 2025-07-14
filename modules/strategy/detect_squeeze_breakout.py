import pandas as pd
from modules.fetch_stock_data import fetch_stock_data
from modules.config import POLYGON_API_KEY

def detect_squeeze_breakout(symbol):
    df = fetch_stock_data(symbol, api_key=POLYGON_API_KEY)
    if df is None or len(df) < 60:
        print(f"[擠壓] {symbol} ➜ 資料不足")
        return None

    required_columns = ['close']
    for col in required_columns:
        if col not in df.columns:
            print(f"[擠壓錯誤] {symbol} 缺少欄位：{col}")
            return None

    df['MA20'] = df['close'].rolling(window=20).mean()
    df['stddev'] = df['close'].rolling(window=20).std()
    df['upper'] = df['MA20'] + (2 * df['stddev'])
    df['lower'] = df['MA20'] - (2 * df['stddev'])
    df['band_width'] = df['upper'] - df['lower']

    recent_bandwidth = df['band_width'].iloc[-5:]

    squeeze = recent_bandwidth.mean() < df['band_width'].rolling(window=50).mean().iloc[-1] * 0.5

    if squeeze:
        print(f"[擠壓策略] {symbol} ➜ 進入擠壓狀態")
        return {
            'symbol': symbol,
            'squeeze': True,
            'bandwidth': recent_bandwidth.mean()
        }
    else:
        return None