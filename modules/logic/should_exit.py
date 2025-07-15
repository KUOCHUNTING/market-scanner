def should_exit(position, current_price):
    entry_price = position["entry_price"]
    direction = position["direction"]

    # === 計算報酬率 ===
    if direction == "做多":
        change = (current_price - entry_price) / entry_price
    else:  # 做空
        change = (entry_price - current_price) / entry_price

    # === 三段鎖利 / 停損邏輯 ===
    stop_loss = -0.05
    first_lock = 0.05
    second_lock = 0.08
    third_lock = 0.12

    # === 第 1 段鎖利（漲超過 5%，回檔 2%）===
    if change >= first_lock and position.get("max_profit", 0) - change >= 0.02:
        return True, "🔒 第一段鎖利（回檔 2%）"

    # === 第 2 段鎖利（漲超過 8%，回檔 3%）===
    if change >= second_lock and position.get("max_profit", 0) - change >= 0.03:
        return True, "🔒 第二段鎖利（回檔 3%）"

    # === 第 3 段鎖利（漲超過 12%，回檔 4%）===
    if change >= third_lock and position.get("max_profit", 0) - change >= 0.04:
        return True, "🔒 第三段鎖利（回檔 4%）"

    # === 停損邏輯 ===
    if change <= stop_loss:
        return True, "❌ 停損觸發"

    return False, ""
