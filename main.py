import os
import time
from datetime import datetime, timedelta
import pandas as pd
from polygon import RESTClient
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD

# 設定 API Key 與推播網址
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
            limit=100
        )

        if not aggs:
            print(f"[WARNING] 無資料（空回傳）：{symbol}")
            return None

        data = []
        for bar in aggs:
            if "t" not in bar or bar["t"] is None:
                continue
            data.append({
                "timestamp": pd.to_datetime(bar["t"], unit='ms'),
                "open": bar.get("o", 0),
                "high": bar.get("h", 0),
                "low": bar.get("l", 0),
                "close": bar.get("c", 0),
                "volume": bar.get("v", 0)
            })

        if not data:
            print(f"[WARNING] 無有效欄位資料：{symbol}")
            return None

        df = pd.DataFrame(data)
        if "timestamp" not in df.columns:
            print(f"[ERROR] 缺少 timestamp 欄位：{symbol}")
            return None

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
    # 實際整合可加入 requests.post 發送到 Webhook

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
            push_to_discord(symbol, signal)

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
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL") or "https://discord.com/api/webhooks/your_webhook_url"
    try:
        data = {"content": content}
        response = requests.post(webhook_url, json=data)
        if response.status_code != 204:
            print(f"[ERROR] Discord 推播失敗：{response.status_code} {response.text}")
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
