def can_enter_new_position(symbol, capital_required):
    # 已經持有該股票
    if symbol in positions:
        return False

    # 同時持股超限
    if len(positions) >= MAX_ACTIVE_POSITIONS:
        print(f"[資金控管] 持股達上限 [{MAX_ACTIVE_POSITIONS}] 檔")
        return False

    # 單檔超出最大投入限制
    if capital_required > MAX_CAPITAL_PER_POSITION:
        print(f"[資金控管] 單檔超出上限 ${MAX_CAPITAL_PER_POSITION:,}：{symbol}")
        return False

    # 資金不足
    if capital_required > capital_left:
        print(f"[資金控管] 資金不足，無法進場 {symbol}")
        return False

    return True