def compute_position_size(latest_price):
    global capital_left

    # ✅ 資金不足直接跳過
    if capital_left < 100:
        print(f"[跳過] 可用資金不足（${capital_left:.2f}），略過建倉")
        return 0, 0

    # 1️⃣ 預設投入金額為總資金的 POSITION_RATIO（如 5%）
    proposed_capital = TOTAL_CAPITAL * POSITION_RATIO

    # 2️⃣ 不能超過剩餘資金
    proposed_capital = min(proposed_capital, capital_left)

    # 3️⃣ 根據股價換算可買股數（整數）
    shares = int(proposed_capital // latest_price)

    # 4️⃣ 股數不得超過 MAX_SHARES_PER_POSITION
    shares = min(shares, MAX_SHARES_PER_POSITION)

    # 5️⃣ 實際投入金額為 shares * price
    capital_used = shares * latest_price

    return shares, capital_used