def fetch_latest_prices_batch(symbols):
    prices = {}
    for symbol in symbols:
        try:
            url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev?adjusted=true&apiKey={POLYGON_API_KEY}"
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            if "results" in data and data["results"]:
                prices[symbol] = data["results"][0]["c"]
            else:
                print(f"[警告] {symbol} ➜ 無回傳價格")
        except Exception as e:
            print(f"[錯誤] {symbol} 價格查詢失敗：{e}")
    return prices