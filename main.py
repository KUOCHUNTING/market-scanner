
import os
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD
from polygon import RESTClient
from datetime import datetime, timedelta
from pytz import timezone

API_KEY = os.getenv("POLYGON_API_KEY") or "YmbcjRd1RA6l3pTlN0NvKRzd7OY4eV8k"
STOCK_LIST_CSV = "filtered_us_stocks_common_only.csv"

def load_stock_list(filepath):
    try:
        df = pd.read_csv(filepath)
        return df['symbol'].tolist()
    except Exception as e:
        print(f"[ERROR] 無法讀取股票清單：{e}")
        return []

def fetch_stock_data(symbol):
    try:
        client = RESTClient(api_key=API_KEY)
        est = timezone("US/Eastern")
        now = datetime.now(est)
        end = now - timedelta(minutes=15)
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

        bars = aggs.results if hasattr(aggs, 'results') else aggs
        if not bars or not isinstance(bars, list):
            return None

        df = pd.DataFrame(bars)
        df['timestamp'] = pd.to_datetime(df['t'], unit='ms')
        df = df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})
        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    except Exception as e:
        print(f"[ERROR] 抓取資料失敗 {symbol}：{e}")
        return None

def run_scanner():
    stock_list = load_stock_list(STOCK_LIST_CSV)

    for symbol in stock_list:
        try:
            df = fetch_stock_data(symbol)
            if df is None or len(df) < 10:
                continue

            rsi = RSIIndicator(close=df['close']).rsi()
            macd = MACD(close=df['close']).macd_diff()
            vwap = (df['volume'] * (df['high'] + df['low'] + df['close']) / 3).cumsum() / df['volume'].cumsum()

            latest_rsi = rsi.iloc[-1]
            latest_macd = macd.iloc[-1]
            latest_vwap = vwap.iloc[-1]
            latest_price = df['close'].iloc[-1]
            latest_open = df['open'].iloc[-1]
            latest_high = df['high'].iloc[-1]
            latest_low = df['low'].iloc[-1]
            latest_volume = df['volume'].iloc[-1]
            avg_volume = df['volume'].mean()
            volume_ratio = latest_volume / avg_volume if avg_volume > 0 else 0

            # 顯示每一支股票的 K棒與指標資料
            print(f"[DATA] {symbol} 最新K棒：")
            print(f"開：{latest_open:.2f} | 高：{latest_high:.2f} | 低：{latest_low:.2f} | 收：{latest_price:.2f} | 量：{latest_volume:,}")
            print(f"[INDICATOR] RSI: {latest_rsi:.1f} | MACD: {latest_macd:.2f} | VWAP: {latest_vwap:.2f} | 量能倍率: {volume_ratio:.2f}x")

            # 判斷訊號（也可印出）
            if latest_rsi > 70 and rsi.iloc[-1] < rsi.iloc[-2]:
                signal_note = "⚠️ 預警 - 空頭轉折"
            if latest_macd < 0 and latest_price < latest_vwap and volume_ratio > 1.5:
                signal_note = "🐶 正式進場 - 空頭"

            signal_note = None
            if latest_rsi < 30 and rsi.iloc[-1] > rsi.iloc[-2]:
                signal_note = "⚠️ 預警 - 多頭轉折"
            if latest_macd > 0 and latest_price > latest_vwap and volume_ratio > 1.5:
                signal_note = "🐸 正式進場 - 多頭"

            if signal_note:
                print(f"[ALERT] {signal_note}：{symbol}")
                print("-" * 60)

        except Exception as e:
            print(f"[ERROR] {symbol} 處理失敗：{e}")

if __name__ == "__main__":
    run_scanner()
