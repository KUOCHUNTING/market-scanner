
import time
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor

def fetch_5min_bars(symbol):
    try:
        dates = pd.date_range(end=datetime.now(), periods=100, freq='5min')
        prices = np.cumsum(np.random.randn(100)) + 100
        volume = np.random.randint(1000, 10000, size=100)
        df = pd.DataFrame({'datetime': dates, 'close': prices, 'volume': volume})
        df.set_index('datetime', inplace=True)
        return df
    except Exception as e:
        print(f"❌ 抓取 {symbol} 資料錯誤：{e}")
        return None

def calculate_indicators(df):
    df['RSI'] = 100 - 100 / (1 + df['close'].pct_change().rolling(14).mean() / df['close'].pct_change().rolling(14).std())
    df['MACD_line'] = df['close'].ewm(span=12).mean() - df['close'].ewm(span=26).mean()
    df['MACD_signal'] = df['MACD_line'].ewm(span=9).mean()
    df['MACD_hist'] = df['MACD_line'] - df['MACD_signal']
    df['K'] = df['close'].rolling(3).mean()
    df['D'] = df['K'].rolling(3).mean()
    df['VWAP'] = (df['close'] * df['volume']).cumsum() / df['volume'].cumsum()
    df['TMO_fast'] = df['close'].diff().rolling(5).mean()
    df['TMO_slow'] = df['TMO_fast'].rolling(3).mean()
    return df

def check_technical_signals(df, symbol):
    try:
        df = calculate_indicators(df)
        last = df.iloc[-1]

        # 多頭共振條件
        bullish = (
            last['TMO_fast'] > last['TMO_slow'] and
            last['RSI'] < 35 and
            last['MACD_hist'] > 0 and
            last['K'] > last['D'] and
            last['close'] > last['VWAP']
        )

        # 空頭共振條件
        bearish = (
            last['TMO_fast'] < last['TMO_slow'] and
            last['RSI'] > 65 and
            last['MACD_hist'] < 0 and
            last['K'] < last['D'] and
            last['close'] < last['VWAP']
        )

        # 預警條件（只滿足其中 2~4 個）
        conditions = [
            last['TMO_fast'] > last['TMO_slow'],
            last['RSI'] < 35,
            last['MACD_hist'] > 0,
            last['K'] > last['D'],
            last['close'] > last['VWAP'],
        ]
        bull_match_count = sum(conditions)

        bear_conditions = [
            last['TMO_fast'] < last['TMO_slow'],
            last['RSI'] > 65,
            last['MACD_hist'] < 0,
            last['K'] < last['D'],
            last['close'] < last['VWAP'],
        ]
        bear_match_count = sum(bear_conditions)

        if bullish:
            return {"symbol": symbol, "type": "正式多單進場", "price": last['close']}
        elif bear_match_count >= 4:
            return {"symbol": symbol, "type": "正式空單進場", "price": last['close']}
        elif bull_match_count >= 3:
            return {"symbol": symbol, "type": "預警多頭訊號", "price": last['close']}
        elif bear_match_count == 3:
            return {"symbol": symbol, "type": "預警空頭訊號", "price": last['close']}
        else:
            return None

    except Exception as e:
        print(f"❌ 訊號判斷錯誤：{e}")
        return None


import requests

def push_to_discord(signal):
    content = f"📢 訊號通知：{{signal['symbol']}}\n類型：{{signal['type']}}\n現價：{{signal['price']:.2f}}\n時間：{{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}}"
    data = {{'content': content}}
    try:
        response = requests.post("https://discord.com/api/webhooks/1373309204810563604/CUhbQ6sFvtNqSsEXxw7TnnMocMyV_VwfDqr7p3iiz3lXFUkzLNZXbzdO9EEEp87pk6lE", json=data)
        if response.status_code != 204:
            print(f"❌ Discord 發送失敗：{{response.status_code}} - {{response.text}}")
    except Exception as e:
        print(f"❌ Discord 發送錯誤：{{e}}")


def process_symbol(symbol):
    try:
        print(f"🔍 開始處理：{symbol}")
        df = fetch_5min_bars(symbol)
        if df is None or df.empty:
            print(f"⚠️ {symbol} 沒有有效資料，略過")
            return

        signal = check_technical_signals(df, symbol)
        if signal:
            print(f"✅ {symbol} 出現訊號：{signal['type']}")
            push_to_discord(signal)
        else:
            print(f"ℹ️ {symbol} 無訊號")

    except Exception as e:
        print(f"❌ {symbol} 執行錯誤：{e}")

def scan_all_symbols(symbols):
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(process_symbol, symbol) for symbol in symbols]
        for future in futures:
            future.result()

def main():
    print("✅ 掃描器啟動成功")
    symbols = ["AAPL", "MSFT", "TSLA", "NVDA", "AMD"]
    print(f"✅ 股票清單載入成功，共 {len(symbols)} 檔")
    print("▶️ 啟動主程式")

    while True:
        scan_all_symbols(symbols)
        print(f"⏳ 等待 60 秒...（下一輪將於 {datetime.now() + timedelta(seconds=60):%H:%M:%S} 執行）")
        time.sleep(60)

if __name__ == "__main__":
    main()
