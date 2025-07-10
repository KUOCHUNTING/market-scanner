from datetime import datetime

def check_exit_and_notify(symbol, latest_price):
    global capital_left

    if symbol not in positions:
        return

    # ✅ 修補持倉資訊
    repair_position(symbol)
    pos = positions[symbol]

    # ✅ 防呆欄位檢查
    required_keys = ["entry_price", "direction", "quantity", "capital_used", "sell_stage", "max_gain", "strategy"]
    for key in required_keys:
        if key not in pos:
            print(f"[錯誤] {symbol} ➜ 缺少欄位：{key} ➜ {pos}")
            return

    entry_price = pos["entry_price"]
    direction = pos["direction"]
    capital_used = pos["capital_used"]
    quantity = pos["quantity"]
    sell_stage = pos["sell_stage"]
    max_gain = pos["max_gain"]
    strategy = pos["strategy"]
    entry_time = pos.get("entry_time")

    # ✅ 防呆處理
    if entry_price is None or entry_price < 0.1 or quantity <= 0:
        print(f"[略過] {symbol} ➜ entry_price={entry_price}, quantity={quantity}，略過出場判斷")
        return

    # ✅ 報酬率計算
    if direction and "多" in direction:
        return_rate = (latest_price - entry_price) / entry_price
    elif direction and "空" in direction:
        return_rate = (entry_price - latest_price) / entry_price
    else:
        print(f"[⚠️方向異常] direction={direction!r}，已設為報酬率 0")
        return_rate = 0.0

    return_rate = round(return_rate * 100, 2)

    # ✅ 更新最高報酬
    if return_rate > max_gain:
        pos["max_gain"] = return_rate
        max_gain = return_rate

    # ✅ 停損 / 三段鎖利邏輯（含追蹤停利）
    reason, exit_ratio = None, 0

    if return_rate <= -DEFAULT_STOP_LOSS:
        reason = f"🛑 停損觸發：報酬率 {return_rate:.2f}%"
        exit_ratio = 1.0
        sell_stage = -1

    elif return_rate >= DEFAULT_TAKE_PROFIT and sell_stage == 0:
        reason = f"🔒 第一段鎖利：報酬率 {return_rate:.2f}%"
        exit_ratio = 0.5
        sell_stage = 1

    elif return_rate >= 8.0 and sell_stage <= 1:
        reason = f"🔒 第二段鎖利：報酬率 {return_rate:.2f}%"
        exit_ratio = 1.0
        sell_stage = 2

    elif max_gain >= TRAIL_TRIGGER and (max_gain - return_rate) >= TRAIL_MARGIN and sell_stage <= 1:
        drop = round(max_gain - return_rate, 2)
        reason = f"🔃 追蹤停利觸發（回落 {drop:.2f}%）"
        exit_ratio = 1.0
        sell_stage = 3

    # ✅ 尚未出場也印出當前狀態
    if reason is None or exit_ratio <= 0:
        now = datetime.now()
        last_push = last_tracking_push_time.get(symbol)

        # 若無推播記錄，或已經超過 3 分鐘，才推播
        if not last_push or (now - last_push) >= timedelta(minutes=3):
            holding_minutes = int((now - entry_time).total_seconds() / 60) if entry_time else 0
            pnl_emoji = "🟢" if return_rate > 0 else "🔴" if return_rate < 0 else "⚪"
            pnl_text = f"{return_rate:.2f}%"

            message = f"🔔【持倉追蹤】{symbol}\n" \
                    f"{pnl_emoji} 報酬率：{pnl_text}\n" \
                    f"進場價：{entry_price:.2f}｜目前價：{latest_price:.2f}\n" \
                    f"策略：{strategy}｜持倉時間：{holding_minutes} 分鐘"
            
            send_discord_message(WEBHOOK_URL, message)

            print(message)
            try:
                requests.post(WEBHOOK_URL, json={"content": message})
            except Exception as e:
                print(f"[推播錯誤] {symbol} ➜ {e}")

            # ✅ 更新推播時間
            last_tracking_push_time[symbol] = now
        return

    # ✅ 計算出場數量與損益金額
    exit_qty = int(quantity * exit_ratio)
    if exit_qty <= 0:
        print(f"[略過] {symbol} ➜ 出場數量為 0")
        return

    pnl = (latest_price - entry_price) if "多" in direction else (entry_price - latest_price)
    profit_dollar = round(pnl * exit_qty, 2)

    capital_left += latest_price * exit_qty
    pos["quantity"] -= exit_qty
    pos["sell_stage"] = sell_stage

    emoji = "✅" if return_rate >= 0 else "⚠️"
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ✅ 策略名稱顯示轉換
    strategy_name_map = {
        "均值回歸": "🎯 均值回歸策略",
        "順勢策略": "🔥 順勢策略",
        "RROV": "📊 RROV 策略"
    }
    strategy_name = strategy_name_map.get(strategy, f"📌 {strategy}")

    # ✅ 推播訊息
    content = (
        f"{emoji} **[出場通知 - {strategy_name}｜{direction}單]** {symbol}\n"
        f"📈 出場價格：${latest_price:.2f} ｜ 數量：{exit_qty} 股\n"
        f"📊 報酬率：{return_rate:.2f}% ｜ 獲利金額：${profit_dollar:.2f}\n"
        f"🔄 原因：{reason}\n"
        f"🕒 時間：{time_str}"
    )

    requests.post(WEBHOOK_URL, json={"content": content})

    # ✅ 出場紀錄
    exit_position(symbol, latest_price, pos)

    if pos["quantity"] <= 0:
        del positions[symbol]
