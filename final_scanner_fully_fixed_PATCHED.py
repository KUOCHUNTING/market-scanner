import requests
POLYGON_API_KEY = "y6h2VA5s_prMdJ2VzTtfFV3bRBdsslEV"
import pandas as pd
from ta.momentum import RSIIndicator
import time

def load_symbols():
    try:
        df = pd.read_csv("filtered_us_stocks_common_only.csv")
        print(f"✅ 股票清單載入成功,共 {len(df)} 檔")
        return df["symbol"].tolist()
    except pd.errors.ParserError:
        print("⚠️ CSV 讀取錯誤，略過")
        return []

def fetch_stock_data(symbol):
    try:
        url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/5/minute/1/2025-05-23/2025-05-23?adjusted=true&sort=asc&limit=1000&apiKey={POLYGON_API_KEY}"
        response = requests.get(url, timeout=10)
        print(f"🔗 {symbol} 回傳狀態: {response.status_code}")
        print(f"📦 回傳內容預覽: {response.text[:200]}")
        data = response.json()
        if "results" not in data:
            print(f"⚠️ {symbol} 無結果欄位，完整內容: {data}")
            return None
        df = pd.DataFrame(data["results"])
        df["t"] = pd.to_datetime(df["t"], unit="ms")
        df = df.rename(columns={"c": "close"})
        df.set_index("t", inplace=True)
        return df
    except Exception as e:
        print(f"❌ {symbol} 抓取失敗: {e}")
        return None

def analyze_indicators(df):
    try:
        rsi = RSIIndicator(close=df["close"]).rsi()
        return rsi
    except Exception as e:
        print(f"❌ 技術指標計算失敗: {e}")
        return None

def check_signal(rsi):
    if rsi is not None and rsi.iloc[-1] < 30:
        return "Buy signal"
    return None

def send_alert(symbol, signal):
    print(f"🚨 {symbol} 訊號: {signal}")

def main():
    symbols = load_symbols()
    for symbol in symbols:
        print(f"🔍 掃描中: {symbol}")
        df = fetch_stock_data(symbol)
        if df is not None:
            rsi = analyze_indicators(df)
            signal = check_signal(rsi)
            if signal:
                send_alert(symbol, signal)

if __name__ == "__main__":
    print("✅ 執行版本：REBUILT_AST_OK")
    main()
