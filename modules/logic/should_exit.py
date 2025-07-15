from modules.config import DEFAULT_STOP_LOSS, DEFAULT_TAKE_PROFIT, TRAIL_TRIGGER, TRAIL_MARGIN
from modules.config import positions

def should_exit(symbol):
    pos = positions.get(symbol)
    if not pos:
        return False

    entry_price = pos["entry_price"]
    direction = pos["direction"]
    latest_price = pos["latest_price"]
    sell_stage = pos["sell_stage"]
    max_gain = pos["max_gain"]

    if not all([entry_price, latest_price, direction]):
        return False

    # 計算報酬率
    if "多" in direction:
        return_rate = (latest_price - entry_price) / entry_price * 100
    else:
        return_rate = (entry_price - latest_price) / entry_price * 100

    # 記錄最高報酬
    if return_rate > max_gain:
        pos["max_gain"] = return_rate
        max_gain = return_rate

    # 出場條件
    if return_rate <= -DEFAULT_STOP_LOSS:
        pos["exit_reason"] = f"🛑 停損觸發：{return_rate:.2f}%"
        pos["exit_ratio"] = 1.0
        return True
    elif return_rate >= DEFAULT_TAKE_PROFIT and sell_stage == 0:
        pos["exit_reason"] = f"🔒 第一段鎖利：{return_rate:.2f}%"
        pos["exit_ratio"] = 0.5
        pos["sell_stage"] = 1
        return True
    elif return_rate >= 8.0 and sell_stage <= 1:
        pos["exit_reason"] = f"🔒 第二段鎖利：{return_rate:.2f}%"
        pos["exit_ratio"] = 1.0
        pos["sell_stage"] = 2
        return True
    elif max_gain >= TRAIL_TRIGGER and (max_gain - return_rate) >= TRAIL_MARGIN and sell_stage <= 1:
        drop = max_gain - return_rate
        pos["exit_reason"] = f"🔃 追蹤停利：回落 {drop:.2f}%"
        pos["exit_ratio"] = 1.0
        pos["sell_stage"] = 3
        return True

    return False
