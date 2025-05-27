
import os
import time
import csv
import requests
from datetime import datetime, timedelta
import pandas as pd
from pytz import timezone
from polygon import RESTClient
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD, EMAIndicator

API_KEY = os.getenv("POLYGON_API_KEY") or "YmbcjRd1RA6l3pTlN0NvKRzd7OY4eV8k"
SCAN_INTERVAL = 60
WEBHOOK_URL = "https://discord.com/api/webhooks/1373309204810563604/CUhbQ6sFvtNqSsEXxw7TnnMocMyV_VwfDqr7p3iiz3lXFUkzLNZXbzdO9EEEp87pk6lE"


def fetch_stock_data(symbol):
    try:
        client = RESTClient(api_key=API_KEY)
        est = timezone("US/Eastern")
        now = datetime.now(est)
        end = now - timedelta(minutes=15)
        start = end - timedelta(minutes=35)

        print(f"[INFO] 正在抓取延遲15分鐘資料：{symbol} - 時間範圍 {start} ~ {end}")
        aggs = client.get_aggs(
            ticker=symbol, multiplier=5, timespan="minute",
            from_=start.strftime("%Y-%m-%d"), to=end.strftime("%Y-%m-%d"),
            limit=100, adjusted=True
        )

        bars = aggs.results if hasattr(aggs, 'results') else aggs
        if not bars or not isinstance(bars, list) or len(bars) == 0:
            print(f"[WARNING] 無法轉換為有效 DataFrame：{symbol}")
            return None

        valid_bars = []
        for bar in bars:
            if not isinstance(bar, dict):
                bar = bar.__dict__
            if all(k in bar for k in ["t", "o", "h", "l", "c", "v"]):
                valid_bars.append({
                    "timestamp": pd.to_datetime(bar["t"], unit='ms'),
                    "open": bar["o"], "high": bar["h"],
                    "low": bar["l"], "close": bar["c"], "volume": bar["v"]
                })

            if len(valid_bars) < 5:
                return None  # 不顯示警告，靜默跳

        df = pd.DataFrame(valid_bars)
        df.set_index("timestamp", inplace=True)
        return df

        try:
            rsi = RSIIndicator(close=df['c']).rsi().iloc[-1]
            macd = MACD(close=df['c']).macd_diff().iloc[-1]
            vwap = (df['v'] * (df['h'] + df['l'] + df['c']) / 3).cumsum() / df['v'].cumsum()
            vwap = vwap.iloc[-1]
            ema5 = df['c'].ewm(span=5, adjust=False).mean().iloc[-1]
            ema20 = df['c'].ewm(span=20, adjust=False).mean().iloc[-1]
            volume_avg = df['v'].rolling(window=20).mean().iloc[-1]
            volume_ratio = df['v'].iloc[-1] / volume_avg if volume_avg != 0 else 0
            ema_cross = "EMA5 > EMA20" if ema5 > ema20 else "EMA5 < EMA20"

            # KD 金叉判斷
            k = StochasticOscillator(high=df['h'], low=df['l'], close=df['c']).stoch()
            d = StochasticOscillator(high=df['h'], low=df['l'], close=df['c']).stoch_signal()
            kd_cross = "金叉" if k.iloc[-2] < d.iloc[-2] and k.iloc[-1] > d.iloc[-1] else "死叉"

            price = df['c'].iloc[-1]

            print(f"[DEBUG] {symbol} 指標：RSI={rsi:.2f}, MACD={macd:+.2f}, VWAP={vwap:.2f}, EMA5={ema5:.2f}, EMA20={ema20:.2f}, 量能={volume_ratio:.2f}, KD={kd_cross}")

             # 訊號邏輯判斷
             signal = None
                if rsi < 30 and macd > 0 and price > vwap:
                    signal = "預警 - 多頭轉折"
                elif rsi > 70 and macd < 0 and price < vwap:
                    signal = "預警 - 空頭轉折"
                elif rsi > 30 and macd > 0 and ema5 > ema20 and volume_ratio > 1.5:
                    signal = "正式進場 - 多頭"
                elif rsi < 70 and macd < 0 and ema5 < ema20 and volume_ratio > 1.5:
                    signal = "正式進場 - 空頭"

                if signal:
                    push_to_discord(symbol, signal, rsi, macd, vwap, price, volume_ratio, ema_cross, kd_cross)
        
        except Exception as e:
            print(f"[ERROR] 技術指標處理失敗：{symbol} - {e}")
            return None
            
        except Exception as e:
            print(f"[ERROR] 抓取資料失敗 {symbol}：{e}")
            return None
def push_to_discord(symbol, signal, rsi, macd, vwap, price, volume_ratio, ema_cross, kd_cross):
    message = f"""```yaml
🐸 [{signal}] {symbol}
💰 價格    : ${price:.2f}
📈 RSI    : {rsi:.2f}
📊 MACD   : {macd:+.2f}
🏷️ VWAP   : {vwap:.2f}
🔥 量能    : {volume_ratio:.1f}x
📐 均線交叉: {ema_cross}
🌀 KD     : {kd_cross}
```"""
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": message})
        print(f"[推播成功] {symbol} → Discord")
    except Exception as e:
        print(f"[推播失敗] {symbol}：{e}")



    
    try:
        response = requests.post(WEBHOOK_URL, json={"content": message})
        if response.status_code != 204:
            print(f"[ERROR] Discord 推播失敗：{response.status_code} - {response.text}")
        else:
            print(f"[DISCORD] 成功推播訊號：{symbol}")
    except Exception as e:
        print(f"[ERROR] 發送 Discord 訊息錯誤：{e}")

def analyze_signal(symbol, df):
    try:
        close = df['close']
        if len(close) < 35:
            return None

        rsi = RSIIndicator(close).rsi().iloc[-1]
        macd = MACD(close).macd_diff().iloc[-1]
        kd = StochasticOscillator(high=df['high'], low=df['low'], close=close)
        k_value = kd.stoch().iloc[-1]
        d_value = kd.stoch_signal().iloc[-1]
        vwap = (df['close'] * df['volume']).cumsum() / df['volume'].cumsum()
        current_price = close.iloc[-1]
        current_vwap = vwap.iloc[-1]
        volume = df['volume'].iloc[-1]
        avg_volume = df['volume'].rolling(window=5).mean().iloc[-2]
        ema_5 = EMAIndicator(close, window=5).ema_indicator().iloc[-1]
        ema_20 = EMAIndicator(close, window=20).ema_indicator().iloc[-1]

        ema_cross = "EMA5 > EMA20" if ema_5 > ema_20 else "EMA5 < EMA20"
        kd_cross = "KD 金叉" if k_value > d_value else "KD 死叉"
        volume_ratio = volume / avg_volume

        if 45 <= rsi <= 65:
            return None

        signal = None
        if rsi < 30 and k_value > d_value and macd < 0:
            signal = "預警 - 多頭轉折"
        elif rsi > 70 and k_value < d_value and macd > 0:
            signal = "預警 - 空頭轉折"
        elif (
            rsi < 45 and macd > 0 and current_price > current_vwap and
            volume_ratio > 1 and ema_5 > ema_20 and k_value > d_value
        ):
            signal = "正式進場 - 多頭"
        elif (
            rsi > 65 and macd < 0 and current_price < current_vwap and
            volume_ratio > 1 and ema_5 < ema_20 and k_value < d_value
        ):
            signal = "正式進場 - 空頭"

        if signal:
            push_to_discord(symbol, signal, rsi, macd, current_vwap, current_price, volume_ratio, ema_cross, kd_cross)
            return signal

        return None
    except Exception as e:
        print(f"[ERROR] 訊號分析錯誤 {symbol}: {e}")
        return None

def load_symbols_from_csv(file_path):
    try:
        df = pd.read_csv(file_path)
        return df['symbol'].tolist()
    except Exception as e:
        print(f"[ERROR] 載入股票清單失敗: {e}")
        return []

def scan_all_symbols(symbols):
    total = len(symbols)
    print(f"▶️ 開始掃描共 {total} 檔股票...")

    for idx, symbol in enumerate(symbols, start=1):
        print(f"▶️ [{idx}/{total}] 處理中：{symbol} ...")
        df = fetch_stock_data(symbol)
        if df is None:
            continue
        signal = analyze_signal(symbol, df)
        if signal:
            print(f"[SIGNAL] {symbol} 出現訊號：{signal}")

if __name__ == "__main__":
    try:
        symbols = load_symbols_from_csv("filtered_us_stocks_common_only.csv")
        while True:
            print(f"🔁 新一輪掃描開始於 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            scan_all_symbols(symbols)
            print(f"⏳ 等待 {SCAN_INTERVAL} 秒後執行下一輪...\n")
            time.sleep(SCAN_INTERVAL)
    except Exception as e:
        print(f"[FATAL ERROR] 主程式崩潰：{e}")
