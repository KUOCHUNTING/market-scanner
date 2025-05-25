
import pandas as pd
import time
import requests
from datetime import datetime
from ta.momentum import RSIIndicator
from ta.trend import MACD, CCIIndicator
from ta.volatility import BollingerBands

# ===== [Discord Webhook 設定] =====
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1373309204810563604/CUhbQ6sFvtNqSsEXxw7TnnMocMyV_VwfDqr7p3iiz3lXFUkzLNZXbzdO9EEEp87pk6lE"

# ===== [股票清單讀取] =====
def load_symbols():
    try:
        df = pd.read_csv("filtered_us_stocks_common_only.csv")
        print(f"✅ 股票清單載入成功，共 {len(df)} 檔")
        return df["symbol"].tolist()
    except Exception as e:
        print(f"❌ 無法載入股票清單：{e}")
        return []

# ===== [推播訊息至 Discord] =====
def push_to_discord(title, message):
    try:
        content = f"**{title}**\n{message}"
        requests.post(DISCORD_WEBHOOK_URL, json={"content": content}, timeout=10)
    except Exception as e:
        print(f"❌ Discord 推播失敗：{e}")

# ===== [技術指標分析邏輯（模擬版）] =====
def analyze_technical_indicators(df):
    try:
        rsi = RSIIndicator(df["close"]).rsi().iloc[-1]
        macd = MACD(df["close"]).macd_diff().iloc[-1]
        if rsi < 30 and macd > 0:
            return "⚠️ 多頭預警訊號：RSI < 30 且 MACD 翻正"
        return None
    except Exception as e:
        return None

# ===== [主掃描函式] =====
def scan_all_symbols(symbols):
    print(f"🔍 開始掃描 {len(symbols)} 檔股票...")
    for idx, symbol in enumerate(symbols):
        try:
            print(f"  ▶️ 掃描第 {idx + 1} 檔：{symbol}")
            df = pd.read_csv(f"mock_data/{symbol}.csv")  # 模擬用，請換成真實資料來源
            signal = analyze_technical_indicators(df)
            if signal:
                print(f"  ✅ {symbol} 出現訊號：{signal}")
                push_to_discord(f"{symbol} 技術指標警示", signal)
        except Exception as e:
            print(f"  ❌ {symbol} 掃描錯誤：{e}")

# ===== [主程式] =====
def main():
    symbols = load_symbols()
    scan_all_symbols(symbols)

if __name__ == "__main__":
    while True:
        print(f"▶️ 啟動主流程（{datetime.now().strftime('%H:%M:%S')}）")
        main()
        print("⏳ 等待 60 秒...
")
        time.sleep(60)
