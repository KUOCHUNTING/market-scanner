
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
        print(f"[DEBUG] 處理中股票：{symbol}")
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
        cleaned_bars = []
        for bar in bars:
            # ✅ 先將 Polygon 的 Agg 物件轉成 dict
            cleaned_bars = []
            for bar in bars:
                # ✅ 如果是 Agg 類型，用 vars() 轉成 dict
                if hasattr(bar, '__dict__'):
                    bar_dict = vars(bar)
                elif isinstance(bar, dict):
                    bar_dict = bar
                else:
                    print(f"[ERROR] 非法 bar 結構: {bar}")
                    continue

                # ✅ 檢查 timestamp (t) 是否存在
                if "t" not in bar_dict or bar_dict["t"] is None:
                    continue

                cleaned_bars.append(bar_dict)

        if not cleaned_bars:
            print(f"[WARNING] 無有效 K 棒資料：{symbol}")
            return None

        df = pd.DataFrame(cleaned_bars)
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
            success_count += 1
            ...
        except Exception as e:
            fail_count += 1
            print(f"[ERROR] {symbol} 處理失敗：{e}")

    print(f"\n[統計] 本輪成功 {success_count} 檔，失敗 {fail_count} 檔，有效率：{round(success_count / (success_count + fail_count + 1e-6) * 100, 2)}%\n")
    
            rsi = RSIIndicator(close=df['close']).rsi()
            macd = MACD(close=df['close']).macd_diff()

            # ✅ 改良版 VWAP（近 5 根的 rolling 計算）
            typical_price = (df['high'] + df['low'] + df['close']) / 3
            vwap_series = (typical_price * df['volume']).rolling(window=5).sum() / df['volume'].rolling(window=5).sum()

            # ✅ 抓出最新一筆資料
            latest_rsi = rsi.iloc[-1]
            latest_macd = macd.iloc[-1]
            latest_vwap = vwap_series.iloc[-1] if not pd.isna(vwap_series.iloc[-1]) else None
            latest_price = df['close'].iloc[-1]
            latest_open = df['open'].iloc[-1]
            latest_high = df['high'].iloc[-1]
            latest_low = df['low'].iloc[-1]
            latest_volume = df['volume'].iloc[-1]
            avg_volume = df['volume'].mean()
            volume_ratio = latest_volume / avg_volume if avg_volume > 0 else 0

            # ✅ 若 VWAP 無效則跳過該股票
            if latest_vwap is None:
                print(f"[WARNING] VWAP 為 NaN，跳過：{symbol}")
                return

            # 顯示每一支股票的 K棒與指標資料
            print(f"[DATA] {symbol} 最新K棒：")
            print(f"開：{latest_open:.2f} | 高：{latest_high:.2f} | 低：{latest_low:.2f} | 收：{latest_price:.2f} | 量：{latest_volume:,}")
            print(f"[INDICATOR] RSI: {latest_rsi:.1f} | MACD: {latest_macd:.2f} | VWAP: {latest_vwap:.2f} | 量能倍率: {volume_ratio:.2f}x")

            # 判斷訊號（也可回傳出去）
            signal_note = None

            # ✅ 空頭訊號判斷
            if latest_macd < 0 and latest_price < latest_vwap and volume_ratio > 1.5:
                signal_note = "🐶 正式進場 - 空頭"
            elif latest_rsi > 70 and rsi.iloc[-1] < rsi.iloc[-2]:
                signal_note = "⚠️ 預警 - 空頭轉折"

            # ✅ 多頭訊號判斷
            elif latest_macd > 0 and latest_price > latest_vwap and volume_ratio > 1.5:
                signal_note = "🐸 正式進場 - 多頭"
            elif latest_rsi < 30 and rsi.iloc[-1] > rsi.iloc[-2]:
                signal_note = "⚠️ 預警 - 多頭轉折"

            # ✅ 只印出有訊號的個股
            if signal_note:
                print("-" * 60)
                print(f"[DATA] {symbol} 最新K棒：")
                print(f"開：{latest_open:.2f} | 高：{latest_high:.2f} | 低：{latest_low:.2f} | 收：{latest_price:.2f} | 量：{latest_volume:,}")
                print(f"[INDICATOR] RSI: {latest_rsi:.1f} | MACD: {latest_macd:.2f} | VWAP: {latest_vwap:.2f} | 倍量: {volume_ratio:.2f}x")
                print(f"[ALERT] {signal_note}：{symbol}")
                print("-" * 60)

        except Exception as e:
            print(f"[ERROR] {symbol} 處理失敗：{e}")

if __name__ == "__main__":
    run_scanner()
