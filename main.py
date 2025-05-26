    
import os
import time
import csv
from datetime import datetime, timedelta
import pandas as pd
from polygon import RESTClient
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD

API_KEY = os.getenv("POLYGON_API_KEY") or "YOUR_API_KEY"
SCAN_INTERVAL = 60

def fetch_stock_data(symbol):
    try:
        client = RESTClient(api_key=API_KEY)
        
        # 固定日期：2025-05-22
        start = datetime(2025, 5, 22)
        end = datetime(2025, 5, 22)

        aggs = client.get_aggs(
            ticker=symbol,
            multiplier=5,
            timespan="minute",
            from_=start.strftime("%Y-%m-%d"),
            to=end.strftime("%Y-%m-%d"),
            limit=100,
            adjusted=True
        )

        # ✅ 這段是修正關鍵：支援 list 或物件格式
        bars = aggs.results if hasattr(aggs, "results") else aggs

        if not bars or not isinstance(bars, list):
            print(f"[WARNING] 無效 bars：{symbol}")
            return None
        # 確保拿到的是 list 格式的 K 線資料
        bars = None
        try:
            if hasattr(aggs, 'results'):  # 是 AggResponse 類型
                bars = aggs.results
            elif isinstance(aggs, list):  # 是 list 類型
                bars = aggs
            else:
                raise ValueError("未知 aggs 類型，無法處理")
        except Exception as e:
            print(f"[ERROR] 處理 aggs 失敗 {symbol}: {e}")
            return None

        if not bars:
            print(f"[WARNING] 無資料（空回傳）：{symbol}")
            return None

        # 開始處理每根 K 線
        data = []
        for bar in bars:
            if not isinstance(bar, dict) or "t" not in bar:
                continue
            data.append({
                "timestamp": pd.to_datetime(bar["t"], unit='ms'),
                "open": bar["o"],
                "high": bar["h"],
                "low": bar["l"],
                "close": bar["c"],
                "volume": bar["v"]
            })

        # [關鍵補上] 避免空 DataFrame 錯誤
        if not aggs or not aggs.results:
            print(f"[WARNING] 無有效K線資料：{symbol}")
            return None

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
