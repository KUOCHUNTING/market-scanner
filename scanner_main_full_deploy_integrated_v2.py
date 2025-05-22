
import os
import time
import pandas as pd
import requests
from datetime import datetime
from ta.momentum import RSIIndicator
from ta.trend import MACD

print("✅ [STAGE 1] 啟動整合版主力掃描器", flush=True)

try:
    POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
    if not POLYGON_API_KEY:
        raise ValueError("❌ 未設定 POLYGON_API_KEY")
    print(f"✅ [STAGE 2] 取得 API KEY：{POLYGON_API_KEY[:6]}***", flush=True)
except Exception as e:
    print(f"❌ [STAGE 2 ERROR] API KEY 啟動錯誤：{e}", flush=True)
    POLYGON_API_KEY = None

try:
    df = pd.read_csv("filtered_us_stocks_common_only.csv")  # 使用你上傳的主清單
    symbols = df["symbol"].tolist()
    print(f"✅ [STAGE 3] 成功載入 {len(symbols)} 檔股票", flush=True)
except Exception as e:
    print(f"❌ [STAGE 3 ERROR] 股票清單載入失敗：{e}", flush=True)
    symbols = []

def simulate_discord_push(symbol, signal_type):
    print(f"📢 Discord 推播：{symbol} - {signal_type}", flush=True)

def simulate_sheets_log(symbol, action, return_pct):
    print(f"📄 寫入 Sheets：{symbol} - {action} - 報酬 {return_pct}%", flush=True)

def process_symbol(symbol, idx):
    try:
        print(f"🔁 掃描第 {idx+1} 檔：{symbol}", flush=True)
        df = pd.DataFrame({ "Close": [10 + i * 0.1 for i in range(100)], "Volume": [1000000 + i*1000 for i in range(100)] })
        close = df["Close"]
        rsi = RSIIndicator(close=close, window=14).rsi()
        macd = MACD(close=close).macd()

        if rsi.iloc[-1] < 30 and macd.iloc[-1] > 0:
            simulate_discord_push(symbol, "多頭正式進場")
            simulate_sheets_log(symbol, "正式進場", +5.1)

        time.sleep(0.2)
    except Exception as e:
        print(f"❌ [技術指標錯誤] {symbol}：{e}", flush=True)

def main():
    print("✅ [STAGE 4] 進入主程式", flush=True)
    if not symbols:
        print("⚠️ 無可掃描股票，結束", flush=True)
        return

    for idx, symbol in enumerate(symbols[:10]):
        process_symbol(symbol, idx)

    print("✅ [STAGE 4] 掃描完成", flush=True)

if __name__ == "__main__":
    try:
        print("✅ [STAGE 5] 執行 main()", flush=True)
        main()
    except Exception as e:
        print(f"❌ [STAGE 5 ERROR] 主程式錯誤：{e}", flush=True)
