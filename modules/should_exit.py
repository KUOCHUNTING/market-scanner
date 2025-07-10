def should_exit(symbol):
    position = positions.get(symbol)
    if not position:
        return False

    direction = position.get("direction")
    entry_price = position.get("entry_price")
    latest_price = get_latest_price(symbol)
    sell_stage = position.get("sell_stage", 0)
    max_gain = position.get("max_gain", 0)

    if not latest_price or entry_price == 0:
        return False
    
    # 計算目前報酬率（多空分流）
    gain_pct = (latest_price - entry_price) / entry_price
    if direction and "空" in direction:
        gain_pct = -gain_pct

    # 更新最大漲幅
    if gain_pct > max_gain:
        positions[symbol]["max_gain"] = gain_pct
        max_gain = gain_pct

    # 三段鎖利邏輯
    if sell_stage == 0 and gain_pct >= 0.03:
        print(f"[🔓 第一段鎖利] {symbol} +{round(gain_pct*100,2)}% ➜ 出場 1/3")
        positions[symbol]["sell_stage"] = 1
        return "partial_1"  # ➜ 觸發第一段賣出
    elif sell_stage == 1 and gain_pct >= 0.06:
        print(f"[🔓 第二段鎖利] {symbol} +{round(gain_pct*100,2)}% ➜ 出場 1/3")
        positions[symbol]["sell_stage"] = 2
        return "partial_2"  # ➜ 觸發第二段賣出
    elif sell_stage == 2 and gain_pct <= (max_gain - 0.02):
        print(f"[🔚 回落出清] {symbol} 高點回落超過 2% ➜ 出清剩餘")
        return "final_exit"  # ➜ 最後全出場

    return False