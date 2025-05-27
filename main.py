    
import os
import time
import csv
from datetime import datetime, timedelta
import pandas as pd
from pytz import timezone
from polygon import RESTClient
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD

API_KEY = os.getenv("POLYGON_API_KEY") or "YOUR_API_KEY"
SCAN_INTERVAL = 60

def fetch_stock_data(symbol):
    try:
        client = RESTClient(api_key=API_KEY)
        # 設定固定時間為美東時間的 2025/5/22 下午 2:30（EST 盤中）
        est = timezone('US/Eastern')
        end = est.localize(datetime(2025, 5, 22, 14, 30))
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

        # ✅ 處理 list 或物件格式的回傳
        bars = None
        if hasattr(aggs, 'results'):
            bars = aggs.results
        elif isinstance(aggs, list):
            bars = aggs
        else:
            print(f"[WARNING] 未知回傳格式（非 results 或 list）：{symbol}")
            return None

        if not bars or not isinstance(bars, list):
            print(f"[WARNING] 無有效K線資料（bars 無效）：{symbol}")
            return None

        # 開始轉換為 DataFrame
        data = []
        for bar in bars:
            # 檢查欄位是否齊全
            if not all(key in bar for key in ["t", "o", "h", "l", "c", "v"]):
                print(f"[WARNING] 無法轉換為有效 DataFrame：{symbol}")
                return None
            data.append({
                "timestamp": pd.to_datetime(bar["t"], unit='ms'),
                "open": bar["o"],
                "high": bar["h"],
                "low": bar["l"],
                "close": bar["c"],
                "volume": bar["v"]
            })

        # 建立 DataFrame
        df = pd.DataFrame(data)
        df.set_index("timestamp", inplace=True)
        return df

    except Exception as e:
        print(f"[ERROR] 抓取資料失敗 {symbol}: {e}")
        return None

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

        if rsi < 30 and macd > 0 and k_value > d_value:
            return "多頭進場訊號"
        elif rsi > 70 and macd < 0 and k_value < d_value:
            return "空頭進場訊號"
        return None
    except Exception as e:
        print(f"[ERROR] 訊號分析錯誤 {symbol}: {e}")
        return None

def push_to_discord(symbol, signal):
    print(f"[DISCORD] 推播訊號：{symbol} - {signal}")

def load_symbols_from_csv(file_path):
    try:
        df = pd.read_csv(file_path)
        return df['symbol'].tolist()
    except Exception as e:
        print(f"[ERROR] 載入股票清單失敗: {e}")
        return []

def save_error_symbol(symbol):
    with open("error_symbols.csv", "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([symbol])

def send_discord_alert(content):
    import requests
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("[警告] 未設定 Discord Webhook，訊息不會發送")
        return
    try:
        data = {"content": content}
        response = requests.post(webhook_url, json=data)
        if response.status_code != 204:
            print(f"[ERROR] Discord 推播失敗：{response.status_code} {response.text}")
        else:
            print(f"[INFO] 成功推播 Discord：{content[:50]}...")
    except Exception as e:
        print(f"[ERROR] 發送 Discord 推播錯誤：{e}")

def scan_all_symbols(symbols):
    total = len(symbols)
    success_count = 0
    skip_count = 0
    print(f"▶️ 開始掃描共 {total} 檔股票...")

    for idx, symbol in enumerate(symbols, start=1):
        print(f"▶️ [{idx}/{total}] 處理中：{symbol} ...")
        df = fetch_stock_data(symbol)
        if df is None:
            skip_count += 1
            continue
        signal = analyze_signal(symbol, df)
        if signal:
            print(f"[SIGNAL] {symbol} 出現訊號：{signal}")
            push_to_discord(symbol, signal)
            send_discord_alert(f"**{symbol}** 出現訊號：{signal}")
            success_count += 1

    print(f"✅ 掃描完成：成功 {success_count} 檔、略過 {skip_count} 檔")

if __name__ == "__main__":
    try:
        symbols = load_symbols_from_csv("filtered_us_stocks_common_only.csv")
        while True:
            print(f"\n🔁 新一輪掃描開始於 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            scan_all_symbols(symbols)
            print(f"⏳ 等待 {SCAN_INTERVAL} 秒後執行下一輪...\n")
            time.sleep(SCAN_INTERVAL)
    except Exception as e:
        print(f"[FATAL ERROR] 主程式崩潰：{e}")
