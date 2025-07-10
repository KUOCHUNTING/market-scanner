def enter_position(symbol, price, direction, signal_note,
                   rsi=None, zscore=None, strategy_name="未標記策略",
                   ema5=None, ema20=None, upper_band=None, lower_band=None, mid_band=None,
                   roc=None, obv=None, vwap=None, confidence_score=None,
                   strategy_display=None):
    global capital_left

    # ✅ 價格合法性檢查（最重要修正點）
    if price is None or price <= 0:
        print(f"[錯誤] {symbol} 建倉失敗 ➜ 價格無效：{price}")
        return

    # ✅ 避免重複建倉
    if symbol in entered_positions:
        print(f"[跳過] {symbol} 已建倉，略過重複進場")
        return

    # ✅ 計算股數與資金
    shares, capital_used = compute_position_size(price)

    # ✅ 防呆判斷：價格 / 股數 / 資金不能為 0
    if shares <= 0 or capital_used <= 0:
        print(f"[跳過] {symbol} 建倉失敗 ➜ 價格={price}｜股數={shares}｜資金=${capital_used:.2f}")
        return

    # ✅ 扣除資金
    capital_left -= capital_used
    print(f"[資金確認] 已扣資金：${capital_used:.2f}，剩餘資金：${capital_left:,.2f}")

    now = datetime.now()

    # ✅ 記錄正式部位資訊（給出場模組使用）
    positions[symbol] = {
        "direction": direction,
        "entry_price": price,
        "quantity": shares,
        "entry_time": now,
        "capital_used": capital_used,
        "sell_stage": 0,
        "max_gain": 0.0,
        "strategy": strategy_name,
        "strategy_display": strategy_display,
        "rsi": rsi,
        "zscore": zscore,
        "ema5": ema5,
        "ema20": ema20,
        "roc": roc,
        "obv": obv,
        "vwap": vwap,
        "confidence_score": confidence_score,
    }

    # ✅ 建倉簡易紀錄
    entered_positions[symbol] = {
        "price": price,
        "direction": direction,
        "capital_used": capital_used,
        "shares": shares,
        "strategy": strategy_name,
        "confidence_score": confidence_score,
    }

    # ✅ 建倉成功輸出
    print(f"[✅紀錄] 已建倉：{symbol} @ ${price:.2f}｜方向：{direction}｜股數：{shares}｜策略：{strategy_display or strategy_name}")