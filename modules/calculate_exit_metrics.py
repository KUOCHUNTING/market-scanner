def calculate_exit_metrics(entry_price, exit_price, shares, entry_time, exit_time, direction="多", symbol=""):
    """
    自動計算出場三大指標（已用總金額計算報酬率）：
    1. 報酬率 (%)（多單 / 空單）
    2. 損益金額 (USD)
    3. 持倉時間（格式：幾分幾秒）

    傳入：
        entry_price: float
        exit_price: float
        shares: int
        entry_time: datetime
        exit_time: datetime
        direction: str（"多" 或 "空"）

    回傳：
        return_rate (float), pnl (float), holding_duration_str (str)
    """
    try:
        # ✅ entry_price 防呆（太低直接中止）
        if entry_price is None or entry_price < 0.1 or shares <= 0:
            print(f"[跳過] 出場計算異常 ➜ entry_price={entry_price}, shares={shares}")
            return None, None, None

        # ✅ 計算進場與出場總金額
        entry_total = entry_price * shares
        exit_total = exit_price * shares

        print(f"[DEBUG] {symbol} ➜ entry={entry_price}, exit={exit_price}, shares={shares}, direction={direction}")

        # 根據方向計算報酬率 (%)
        if direction and "空" in direction:
            pnl = (entry_price - exit_price) * shares
            return_rate = pnl / entry_total * 100

        elif direction and "多" in direction:
            pnl = (exit_price - entry_price) * shares
            return_rate = pnl / entry_total * 100

        else:
            return_rate = 0.0
            pnl = 0.0
            print(f"[⚠️ 方向異常] direction={direction!r}")

        # ✅ 損益 debug 訊息（放這裡）
        print(f"[DEBUG] 損益={pnl:.2f}｜報酬率={return_rate:.2f}%｜entry總={entry_total:.2f}｜exit總={exit_total:.2f}")

        # ✅ 報酬率與損益防呆過濾
        if return_rate > 500 or return_rate < -90:
            print(f"[跳過] 報酬率異常（{return_rate:.2f}%）")
            return None, None, None

        print(f"[DEBUG] ➜ {symbol} entry={entry_price}｜exit={exit_price}｜shares={shares}｜報酬率={return_rate:.6f}%")

        if abs(pnl) > entry_total * 3:
            print(f"[跳過] 損益異常（${pnl:.2f}）➜ 超過進場金額三倍")
            return None, None, None
        
        # ✅ 持倉時間格式轉換（幾分幾秒）
        holding_delta = exit_time - entry_time
        total_seconds = int(holding_delta.total_seconds())
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        holding_duration_str = f"{minutes}分{seconds}秒"

        return round(return_rate, 4), round(pnl, 2), holding_duration_str

    except Exception as e:
        print(f"[❌ 錯誤] 無法計算出場指標：{e}")
        return None, None, None