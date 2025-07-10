from datetime import datetime

def exit_position(symbol, current_price, position_data):
    from datetime import datetime
    exit_time = datetime.now()

    # 提取部位資訊
    entry_price = position_data['entry_price']
    shares = position_data['shares']
    entry_time = position_data['entry_time']

    # 🔧 如果 entry_time 是字串，轉為 datetime
    if isinstance(entry_time, str):
        try:
            entry_time = datetime.fromisoformat(entry_time)
        except:
            print(f"[錯誤] entry_time 無法轉換：{entry_time}")
            return

    # ✅ 防呆判斷：若為補值或股數為 0，直接跳過
    if entry_price is None or entry_price <= 0.05 or shares <= 0:
        print(f"[跳過] {symbol} ➜ 出場無效（entry_price={entry_price}, shares={shares}）")
        return

    # ✅ 計算出場績效指標
    return_rate, pnl, holding_minutes = calculate_exit_metrics(
        entry_price=entry_price,
        exit_price=current_price,
        shares=shares,
        entry_time=entry_time,
        exit_time=exit_time,
        direction = position_data['direction'],        # ← ✅ 關鍵參數！
        symbol=symbol              
    )

    # ✅ 報酬率計算 debug（這行就放這裡）
    if return_rate is None:
        print(f"[❌ 報酬率無效] {symbol} ➜ 可能被過濾或價格異常")
    else:
        print(f"[✅ 報酬率 OK] {symbol} ➜ {return_rate:.4f}%")

    # ✅ 這行就是你要放的位置 ✅
    if return_rate < -90 or return_rate > 500:
        print(f"[跳過] {symbol} ➜ 報酬率異常（{return_rate:.2f}%），可能是假價格")
        return

    # 如果報酬率計算失敗（None）
    if return_rate is None:
        print(f"[跳過] {symbol} ➜ 出場計算失敗，略過寫入")
        return

    # ✅ 寫入出場紀錄
    write_exit_to_sheet(
        symbol=symbol,
        entry_time=entry_time,
        exit_time=exit_time,
        return_rate=return_rate,
        pnl=pnl,
        holding_minutes=holding_minutes,
        exit_price=exit_price,  # ✅ 新增：實際出場價格
        rsi=position_data.get("rsi"),
        zscore=position_data.get("zscore"),
        roc=position_data.get("roc"),
        obv=position_data.get("obv"),
        vwap=position_data.get("vwap"),
        ema5=position_data.get("ema5"),
        ema20=position_data.get("ema20"),
        strategy_name=position_data.get("strategy_display", "未知策略")
    )

    print(f"[📤 出場完成] {symbol} ➜ 損益：${pnl:.2f}｜報酬率：{return_rate:.2f}%｜持倉：{holding_minutes} 分鐘")
