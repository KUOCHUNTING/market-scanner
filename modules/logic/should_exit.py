from datetime import datetime
from modules.config import DEFAULT_STOP_LOSS, DEFAULT_TAKE_PROFIT, TRAIL_TRIGGER, TRAIL_MARGIN

def should_exit(symbol, position, current_price):
    entry_price = position["entry_price"]
    direction = position["direction"]
    sell_stage = position.get("sell_stage", 0)
    max_gain = position.get("max_gain", 0)
    entry_time = position.get("entry_time")
    holding_minutes = int((datetime.now() - entry_time).total_seconds() / 60) if entry_time else 0

    # === 計算報酬率 ===
    if "多" in direction:
        return_rate = (current_price - entry_price) / entry_price * 100
    else:
        return_rate = (entry_price - current_price) / entry_price * 100

    # ✅ 更新最大報酬
    if return_rate > max_gain:
        position["max_gain"] = return_rate
        max_gain = return_rate

    # ✅ 判斷是否出場
    reason, exit_ratio = None, 0
    if return_rate <= -DEFAULT_STOP_LOSS:
        reason = f"🛑 停損觸發：{return_rate:.2f}%"
        exit_ratio = 1.0
        position["sell_stage"] = -1
    elif return_rate >= DEFAULT_TAKE_PROFIT and sell_stage == 0:
        reason = f"🔒 第一段鎖利：{return_rate:.2f}%"
        exit_ratio = 0.5
        position["sell_stage"] = 1
    elif return_rate >= 8.0 and sell_stage <= 1:
        reason = f"🔒 第二段鎖利：{return_rate:.2f}%"
        exit_ratio = 1.0
        position["sell_stage"] = 2
    elif max_gain >= TRAIL_TRIGGER and (max_gain - return_rate) >= TRAIL_MARGIN and sell_stage <= 1:
        drop = max_gain - return_rate
        reason = f"🔃 追蹤停利：回落 {drop:.2f}%"
        exit_ratio = 1.0
        position["sell_stage"] = 3

    return exit_ratio > 0, reason
