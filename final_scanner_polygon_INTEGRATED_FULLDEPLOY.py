
# final_scanner_polygon_INTEGRATED_FULLDEPLOY.py
import os
import time
import requests
import pandas as pd
import threading
from datetime import datetime, timedelta
from polygon.rest import RESTClient
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

POLYGON_API_KEY = "sRnfK4Nqsa8xTHXC0gBeNE3uh11_Q4ln"
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1373309204810563604/CUhbQ6sFvtNqSsEXxw7TnnMocMyV_VwfDqr7p3iiz3lXFUkzLNZXbzdO9EEEp87pk6lE"
SHEET_ID = "14SSmjk2Ae3rqx0VyiVoVWBXpq0NVNvsLs1RWckuX4Ko"
SCAN_INTERVAL = 60
TESTMODE = False  # 部署用正式掃描全部

def update_price_if_missing():
    df = pd.read_csv("filtered_us_stocks_common_only.csv")
    if 'price' not in df.columns:
        print("⚠️ 偵測到缺少 price 欄位，正在自動補上...")
        client = RESTClient(POLYGON_API_KEY)
        prices = []
        end = datetime.utcnow()
        start = end - timedelta(days=2)
        for symbol in df["symbol"]:
            try:
                aggs = client.get_aggs(
                    ticker=symbol,
                    multiplier=1,
                    timespan="day",
                    from_=start.strftime("%Y-%m-%d"),
                    to=end.strftime("%Y-%m-%d"),
                    limit=1
                )
                if aggs:
                    prices.append(aggs[0].close)
                else:
                    prices.append(None)
                print(f"✅ {symbol} 價格：{prices[-1]}")
            except Exception as e:
                print(f"❌ {symbol} 抓取失敗：{e}")
                prices.append(None)
            time.sleep(0.2)
        df['price'] = prices
        df.to_csv("filtered_us_stocks_common_only.csv", index=False)
        print("✅ 已補上 price 欄位")
    else:
        print("✅ price 欄位已存在，無需補抓")

def load_symbols():
    df = pd.read_csv("filtered_us_stocks_common_only.csv")
    filtered = df[(df['price'] >= 1) & (df['price'] <= 10)]
    if TESTMODE:
        return filtered["symbol"].tolist()[:5]
    return filtered["symbol"].tolist()

def push_to_discord(title, content):
    try:
        msg = {"content": f"**{title}**\n{content}"}
        requests.post(DISCORD_WEBHOOK, json=msg, timeout=10)
    except Exception as e:
        print(f"❌ Discord 發送失敗：{e}")

def write_to_sheet(symbol, signal_type, info):
    try:
        creds = Credentials.from_service_account_file("gspread_key.json.json")
        service = build("sheets", "v4", credentials=creds)
        sheet = service.spreadsheets()
        row = [[datetime.now().strftime("%Y-%m-%d %H:%M:%S"), symbol, signal_type, info]]
        sheet.values().append(spreadsheetId=SHEET_ID,
                              range="訊號紀錄!A:D",
                              valueInputOption="RAW",
                              body={"values": row}).execute()
    except Exception as e:
        print(f"❌ Sheets 寫入失敗：{e}")

def analyze_signal(df):
    try:
        rsi = RSIIndicator(df["close"]).rsi().iloc[-1]
        macd = MACD(df["close"]).macd_diff().iloc[-1]
        so = StochasticOscillator(df["high"], df["low"], df["close"])
        kd_k = so.stoch().iloc[-1]
        kd_d = so.stoch_signal().iloc[-1]
        tmo = df["close"].diff().rolling(window=5).mean().iloc[-1]

        if rsi < 30 and macd > 0 and kd_k > kd_d:
            return "⚠️ 多頭搶轉折"
        if rsi > 70 and macd < 0 and kd_k < kd_d:
            return "⚠️ 空頭翻轉"
        if rsi > 50 and macd > 0 and tmo > 0:
            return "✅ 正式多頭"
        if rsi < 50 and macd < 0 and tmo < 0:
            return "🔻 正式空頭"
        return None
    except:
        return None

def fetch_data(symbol):
    try:
        end = datetime.utcnow()
        start = end - timedelta(days=2)
        client = RESTClient(api_key)
        aggs = client.get_aggs(...)
        bars = client.get_aggs(
                ticker=symbol,
                multiplier=5,
                timespan="minute",
                from_=start.strftime("%Y-%m-%d"),
                to=end.strftime("%Y-%m-%d"),
                limit=100,
                adjusted=True
            )
        df = pd.DataFrame([{
            "timestamp": b.timestamp,
             "open": b.open,
             "high": b.high,
             "low": b.low,
             "close": b.close,
             "volume": b.volume
        } for b in bars])
        return df
    except Exception as e:
        print(f"❌ 無法取得 {symbol} 資料：{e}")
        return None

def process_symbol(symbol):
    df = fetch_data(symbol)
    if df is not None and len(df) > 20:
        signal = analyze_signal(df)
        if signal:
            push_to_discord(symbol, signal)
            write_to_sheet(symbol, signal, "由技術指標觸發")
            print(f"✅ {symbol} 觸發訊號：{signal}")
        else:
            print(f"... {symbol} 無訊號")
    else:
        print(f"❌ {symbol} 無有效資料")

def scan_all_symbols(symbols):
    threads = []
    for symbol in symbols:
        t = threading.Thread(target=process_symbol, args=(symbol,))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()

if __name__ == "__main__":
    print("✅ 啟動掃描器")
    update_price_if_missing()
    while True:
        print(f"▶️ 新一輪掃描開始：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        try:
            symbols = load_symbols()
            print(f"📊 共載入 {len(symbols)} 檔股票")
            scan_all_symbols(symbols)
        except Exception as e:
            print(f"⚠️ 主程式錯誤：{e}")
        print(f"⏳ 等待 {SCAN_INTERVAL} 秒...\n")
        time.sleep(SCAN_INTERVAL)
