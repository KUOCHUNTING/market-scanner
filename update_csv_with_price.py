# update_csv_with_price.py
from polygon.rest import RESTClient
from datetime import datetime, timedelta
import pandas as pd
import time

API_KEY = "sRnfK4Nqsa8xTHXC0gBeNE3uh11_Q4ln"
INPUT_FILE = "filtered_us_stocks_common_only.csv"
OUTPUT_FILE = "filtered_us_stocks_common_only.csv"  # 直接覆蓋原檔

def fetch_price(symbol, client):
    try:
        end = datetime.utcnow()
        start = end - timedelta(days=2)
       aggs = client.get_aggs(
    ticker=symbol,
    multiplier=1,
    timespan="day",
    from_=start.strftime("%Y-%m-%d"),
    to=end.strftime("%Y-%m-%d"),
    limit=1
)
        if aggs:
            return aggs[0].close
    except Exception as e:
        print(f"❌ {symbol} 抓取失敗：{e}")
    return None

def main():
    df = pd.read_csv(INPUT_FILE)
    if 'symbol' not in df.columns:
        df.columns = ['symbol'] + list(df.columns[1:])  # 確保第一欄叫 symbol

    client = RESTClient(API_KEY)
    prices = []
    print("🚀 開始抓取前 20 檔股價...")

    for symbol in df['symbol'][:20]:  # 測試只抓前 20 檔
        price = fetch_price(symbol, client)
        prices.append(price)
        print(f"✅ {symbol} 價格：{price}")
        time.sleep(0.3)  # 防止過快被限流

    df = df[:20].copy()
    df['price'] = prices
    df.to_csv(OUTPUT_FILE, index=False)
    print("✅ 已完成 price 欄位更新，請重新執行主程式")

if __name__ == "__main__":
    main()
