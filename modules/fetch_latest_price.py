def fetch_latest_price(symbol):
    url = f"https://api.polygon.io/v2/last/trade/{symbol}?apiKey={POLYGON_API_KEY}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        # ✅ 防呆處理
        if "results" in data and "p" in data["results"]:
            return data["results"]["p"]  # "p" 是 price
        else:
            raise ValueError(f"Polygon 回傳格式異常：{data}")
    
    except Exception as e:
        print(f"[錯誤] 抓取 {symbol} 最新價格失敗：{e}")
        return None