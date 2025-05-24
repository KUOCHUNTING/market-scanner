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
        # 模擬抓資料用 df
        df = pd.DataFrame()
        return df
    except Exception as e:
        print(f"❌ 無法取得 {symbol} 資料: {e}")
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
