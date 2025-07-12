def repair_position(symbol):
    if symbol not in positions:
        return
    pos = positions[symbol]

    # 防呆補欄位
    if "entry_price" not in pos or pos["entry_price"] is None:
        print(f"[❌ 錯誤] {symbol} ➜ 缺少 entry_price ➜ 建議檢查建倉同步流程")
        return  # ❌ 不自動補 0.01

    if "sell_stage" not in pos:
        pos["sell_stage"] = 0

    if "max_gain" not in pos:
        pos["max_gain"] = 0.0

    if "capital_used" not in pos:
        pos["capital_used"] = 0.0

    if "quantity" not in pos:
        pos["quantity"] = 0

    if "direction" not in pos:
        pos["direction"] = "多"  # 預設為多單