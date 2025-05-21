import pandas as pd
from ta.momentum import RSIIndicator
import yfinance as yf
import time

def load_symbols():
    try:
        df = pd.read_csv('filtered_us_stocks_common_only.csv')
        if 'symbol' in df.columns:
            return df['symbol'].dropna().tolist()
        else:
            return df.iloc[:, 0].dropna().tolist()
    except Exception as e:
        print(f'⚠️ 載入股票清單錯誤:{e}')
        return []

def main():
    symbols = load_symbols()
    for idx, symbol in enumerate(symbols):
        print(f"🔍 正在掃描第 {idx + 1} 檔股票：{symbol}")
        try:
            data = yf.download(symbol, period="5d", interval="5m", prepost=True, auto_adjust=True)
            if len(data) < 20:
                continue

            # 修正：一定要是一維 Series
            close = data["Close"]
            data["rsi"] = RSIIndicator(close=close, window=14).rsi()

            # ... 其他指標也都要確保用 data["欄名"]，不要用 data[["欄名"]]
            # 例如: macd = MACD(close=close, ...)
            #      volume = data["Volume"]

            # 你的判斷邏輯
            latest = data.iloc[-1]
            price_change_pct = (latest["Close"] - data["Close"].iloc[-6]) / data["Close"].iloc[-6] * 100
            rsi_val = latest["rsi"]

            if price_change_pct > 3 and rsi_val > 70:
                print(f"🚀 訊號成立:{symbol} 價格漲幅 + RSI 共振")

        except Exception as e:
            print(f'❌ {symbol} 技術指標處理錯誤:{str(e)}')
            print(f"❌ {symbol} 資料抓取失敗：{e}")

if __name__ == "__main__":
    while True:
        main()
        time.sleep(30)
