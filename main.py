    
import os
import time
import csv
from datetime import datetime, timedelta
import pandas as pd
from pytz import timezone
from polygon import RESTClient
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD

API_KEY = os.getenv("POLYGON_API_KEY") or "YmbcjRd1RA6l3pTlN0NvKRzd7OY4eV8k"
SCAN_INTERVAL = 60

def fetch_stock_data(symbol):
    try:
        # 初始化 Polygon API 客戶端
        client = RESTClient(api_key=API_KEY)
        
        # 設定美東時間（US/Eastern）
        est = timezone("US/Eastern")
        now = datetime.now(est)

        # ⭐ 15分鐘延遲處理：資料只能抓到現在時間 - 15 分鐘
        delay_minutes = 15
        end = now - timedelta(minutes=delay_minutes)
        start = end - timedelta(minutes=35)  # 抓近 7 根K線資料（5分鐘線）

        print(f"[INFO] 正在抓取延遲15分鐘資料：{symbol} - 時間範圍 {start} ~ {end}")

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
            print(f"[ERROR] 無法處理 aggs 結構：{symbol}")
            return None

        if not bars or not isinstance(bars, list) or len(bars) == 0:
            print(f"[DEBUG] aggs 原始資料：{aggs}")
            print(f"[WARNING] 無法轉換為有效 DataFrame：{symbol}")
            return None

        if not bars or not isinstance(bars, list) or len(bars) == 0:
            print(f"[WARNING] 無法轉換為有效 DataFrame：{symbol}")
            return None
            
        # ✅ 關鍵修正：支援 Agg 回傳格式
        if hasattr(aggs, 'results'):
            bars = aggs.results
        elif isinstance(aggs, list):
            bars = aggs
        else:
            print(f"[WARNING] 未知回傳格式（非 results 或 list）：{symbol}")
            return None

        if not bars or not isinstance(bars, list):
            print(f"[WARNING] 無效K線資料（bars 無效）：{symbol}")
            return None

        # 轉換為 DataFrame
        data = []
        print(f"[DEBUG] {symbol} bars 數量：{len(bars)}")
        for bar in bars:
            # 強制 bar 轉為 dict（有些是 Agg 類型）
            if not isinstance(bar, dict):
                bar = bar.__dict__  # ✅ 解開 Agg 類型成字典
            if not all(k in bar for k in ["t", "o", "h", "l", "c", "v"]):
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

        df = pd.DataFrame(data)
        df.set_index("timestamp", inplace=True)
        return df

    except Exception as e:
        print(f"[ERROR] 抓取資料失敗 {symbol}：{e}")
        return None

def analyze_signal(symbol, df):
    try:
        close = df['close']
        if len(close) < 35:
            return None

        # 技術指標
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
        ema_5 = close.ewm(span=5, adjust=False).mean().iloc[-1]
        ema_20 = close.ewm(span=20, adjust=False).mean().iloc[-1]

        # 判斷補充文字
        ema_cross = "EMA5 > EMA20" if ema_5 > ema_20 else "EMA5 < EMA20"
        kd_cross = "KD 金叉" if k_value > d_value else "KD 死叉"
        volume_ratio = volume / avg_volume

        # 避開半山腰 RSI
        if 45 <= rsi <= 65:
            return None

        # 訊號分類判斷
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

        # 回傳格式化訊號
        if signal:
            push_to_discord(symbol, signal, rsi, macd, current_vwap, current_price, volume_ratio, ema_cross, kd_cross)
            return signal

        return None
    except Exception as e:
        print(f"[ERROR] 訊號分析錯誤 {symbol}: {e}")
        return None

def push_to_discord(symbol, signal, rsi, macd, vwap, price, volume_ratio, ema_cross, kd_cross):
    # 決定 emoji 前綴
    if "預警" in signal:
        prefix = "⚠️"
    elif "正式進場 - 多頭" in signal:
        prefix = "🐸"
    elif "正式進場 - 空頭" in signal:
        prefix = "🐶"
    else:
        prefix = ""

    # 推播訊息內容（格式化為固定寬度）
    message = f"""```yaml
{prefix} [{signal}] {symbol}
💰 價格    : ${price:.2f}
📈 RSI    : {rsi:.2f}
📊 MACD   : {macd:+.2f}
🏷️ VWAP   : {vwap:.2f}
🔥 量能    : {volume_ratio:.1f}x
📐 均線交叉: {ema_cross}
🌀 KD     : {kd_cross}
```"""

    print("[DISCORD] 推播訊號：\\n" + message)

    # ✅ 可啟用 webhook 推播
    import requests
    webhook_url = "https://discord.com/api/webhooks/1373309204810563604/CUhbQ6sFvtNqSsEXxw7TnnMocMyV_VwfDqr7p3iiz3lXFUkzLNZXbzdO9EEEp87pk6lE"
    requests.post(webhook_url, json={"content": message})
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
