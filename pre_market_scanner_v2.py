import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from polygon import RESTClient
import schedule
import time

API_KEY = os.getenv("POLYGON_API_KEY", "YOUR_KEY_HERE")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "YOUR_WEBHOOK_HERE")

SYMBOL_LIST = ["TSLA", "NVDA", "AMD", "AAPL", "GME", "AMC"]

def fetch_pre_market_data(symbol):
    now = datetime.utcnow()
    today_str = now.strftime("%Y-%m-%d")
    start_time = f"{today_str}T04:00:00Z"  # 美東 04:00 開始
    end_time = now.isoformat() + "Z"

    try:
        client = RESTClient(API_KEY)
        bars = client.get_aggs(
            symbol=symbol,
            multiplier=5,
            timespan="minute",
            from_=start_time,
            to=end_time,
            limit=500
        )
        df = pd.DataFrame([bar.__dict__ for bar in bars])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        print(f"[錯誤] {symbol} 抓取失敗：{e}")
        return None

def push_to_discord(symbol, change_pct, volume, last_price):
    msg = f"⚠️**[盤前異動警示]** ⚠️\n"
    msg += f"📈 股票：{symbol}\n"
    msg += f"💵 價格：{last_price:.2f}\n"
    msg += f"📊 漲跌幅：{change_pct:.2f}%\n"
    msg += f"🔁 成交量：{volume:,}\n"
    requests.post(DISCORD_WEBHOOK_URL, json={"content": msg})

def analyze_pre_market(symbol):
    df = fetch_pre_market_data(symbol)
    if df is None or df.empty:
        return

    volume_sum = df['volume'].sum()
    open_price = df['open'].iloc[0]
    last_price = df['close'].iloc[-1]
    change_pct = (last_price - open_price) / open_price * 100

    if abs(change_pct) > 5 and volume_sum > 500000:
        print(f"[推播] {symbol} 漲跌 {change_pct:.2f}%，量 {volume_sum}")
        push_to_discord(symbol, change_pct, volume_sum, last_price)

def run_pre_market_scan():
    print(f"\n🚀 執行盤前掃描：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    for symbol in SYMBOL_LIST:
        analyze_pre_market(symbol)

# 每 5 分鐘執行一次
schedule.every(5).minutes.do(run_pre_market_scan)

if __name__ == "__main__":
    run_pre_market_scan()  # 啟動時先掃一次
    while True:
        schedule.run_pending()
        time.sleep(1)
