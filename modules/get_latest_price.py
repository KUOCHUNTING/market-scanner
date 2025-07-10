def get_latest_price(symbol):
    position = positions.get(symbol)
    if position and "latest_price" in position:
        return position["latest_price"]
    else:
        print(f"[⚠️ 無法取得價格] {symbol} 缺少 latest_price")
        return None