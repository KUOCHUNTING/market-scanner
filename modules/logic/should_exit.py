# ✅ 出場條件邏輯（停損、鎖利、追蹤停利）
from modules.config import DEFAULT_STOP_LOSS, DEFAULT_TAKE_PROFIT, TRAIL_TRIGGER, TRAIL_MARGIN

def should_exit(position, current_price):
    entry_price = position["entry_price"]
    direction = position["direction"]
    sell_stage = position.get("sell_stage", 0)
    max_gain = position.get("max_gain", 0)

    if direction == "做多":
        return_rate = (current_price - entry_price) / entry_price * 100
    elif direction == "做空":
        return_rate = (entry_price - current_price) / entry_price * 100
    else:
        return False, "❌ 無效方向"

    # 更新最高報酬
    if return_rate > max_gain:
        position["max_gain"] = return_rate
        max_gain = return_rate

    # 出場邏輯
    if return_rate <= -DEFAULT_STOP_LOSS:
        return True, f"🛑 停損觸發：報酬率 {return_rate:.2f}%"
    elif return_rate >= DEFAULT_TAKE_PROFIT and sell_stage == 0:
        position["sell_stage"] = 1
        return True, f"🔒 第一段鎖利：報酬率 {return_rate:.2f}%"
    elif return_rate >= 8 and sell_stage <= 1:
        position["sell_stage"] = 2
        return True, f"🔒 第二段鎖利：報酬率 {return_rate:.2f}%"
    elif max_gain >= TRAIL_TRIGGER and (max_gain - return_rate) >= TRAIL_MARGIN and sell_stage <= 2:
        position["sell_stage"] = 3
        drop = round(max_gain - return_rate, 2)
        return True, f"🔃 追蹤停利觸發（回落 {drop:.2f}%）"

    return False, None
