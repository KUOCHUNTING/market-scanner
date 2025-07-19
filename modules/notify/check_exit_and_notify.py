from datetime import datetime, timedelta
from modules.notify.discord_push import send_discord_message
from modules.exit.execute_exit import execute_exit as core_exit
from modules.config import (
    DEFAULT_STOP_LOSS,
    DEFAULT_TAKE_PROFIT,
    TRAIL_TRIGGER,
    TRAIL_MARGIN,
    WEBHOOK_URL
)
from modules.repair_position import repair_position
from modules.indicator_cache import get_cached_indicators

# 全域管理（建議由主控傳入）
positions = {}
capital_left = 0
last_tracking_push_time = {}

def check_exit_and_notify(symbol, latest_price):
    global capital_left

    if symbol not in positions:
        return

    # ✅ 修補缺失欄位
    repair_position(symbol)
    pos = positions[symbol]

    # ✅ 防呆檢查
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

    # ✅ 計算報酬率
    if "多" in direction:
        return_rate = (latest_price - entry_price) / entry_price
    elif "空" in direction:
        return_rate = (entry_price - latest_price) / entry_price
    else:
        print(f"[⚠️方向異常] direction={direction!r}")
        return_rate = 0.0

    return_rate_pct = round(return_rate * 100, 2)

    # ✅ 更新最高報酬率
    if return_rate_pct > max_gain:
        pos["max_gain"] = return_rate_pct
        max_gain = return_rate_pct

    # ✅ 判斷出場條件
    reason, exit_ratio = None, 0
    if return_rate_pct <= -DEFAULT_STOP_LOSS:
        reason = f"🛑 停損觸發：報酬率 {return_rate_pct:.2f}%"
        exit_ratio = 1.0
        sell_stage = -1
    elif return_rate_pct >= DEFAULT_TAKE_PROFIT and sell_stage == 0:
        reason = f"🔒 第一段鎖利：報酬率 {return_rate_pct:.2f}%"
        exit_ratio = 0.5
        sell_stage = 1
    elif return_rate_pct >= 8.0 and sell_stage <= 1:
        reason = f"🔒 第二段鎖利：報酬率 {return_rate_pct:.2f}%"
        exit_ratio = 1.0
        sell_stage = 2
    elif max_gain >= TRAIL_TRIGGER and (max_gain - return_rate_pct) >= TRAIL_MARGIN and sell_stage <= 1:
        drop = round(max_gain - return_rate_pct, 2)
        reason = f"🔃 追蹤停利觸發（回落 {drop:.2f}%）"
        exit_ratio = 1.0
        sell_stage = 3

    # ✅ 追蹤推播（每 3 分鐘一次）
    now = datetime.now()
    if reason is None or exit_ratio <= 0:
        last_push = last_tracking_push_time.get(symbol)
        if not last_push or (now - last_push) >= timedelta(minutes=3):
            holding_minutes = int((now - entry_time).total_seconds() / 60) if entry_time else 0
            pnl_emoji = "🟢" if return_rate > 0 else "🔴" if return_rate < 0 else "⚪"
            message = (
                f"🔔【持倉追蹤】{symbol}\n"
                f"{pnl_emoji} 報酬率：{return_rate_pct:.2f}%\n"
                f"進場價：{entry_price:.2f}｜目前價：{latest_price:.2f}\n"
                f"策略：{strategy}｜持倉時間：{holding_minutes} 分鐘"
            )
            send_discord_message(WEBHOOK_URL, message)
            print(message)
            last_tracking_push_time[symbol] = now
        return

    # ✅ 出場處理（交由核心模組處理寫入與推播）
    exit_qty = int(quantity * exit_ratio)
    if exit_qty <= 0:
        print(f"[略過] {symbol} ➜ 出場數量為 0")
        return

    # ✅ 呼叫核心出場流程
    core_exit(
        symbol=symbol,
        entry_time=entry_time,
        exit_price=latest_price,
        entry_price=entry_price,
        rsi=pos.get("rsi"),
        zscore=pos.get("zscore"),
        roc=pos.get("roc"),
        obv=pos.get("obv"),
        vwap=pos.get("vwap"),
        ema5=pos.get("ema5"),
        ema20=pos.get("ema20"),
        strategy_name=strategy
    )

    # ✅ 更新剩餘持倉與資金
    capital_left += latest_price * exit_qty
    pos["quantity"] -= exit_qty
    pos["sell_stage"] = sell_stage

    if pos["quantity"] <= 0:
        del positions[symbol]
import threading
from datetime import datetime
from modules.notify.check_exit_and_notify import check_exit_and_notify

_positions_ref = None  # 要從主程式注入
def set_positions_ref(pos_dict):
    global _positions_ref
    _positions_ref = pos_dict

def schedule_exit_check(interval: int = 10):
    """
    定期掃描所有持倉，呼叫 check_exit_and_notify()
    """
    if not _positions_ref:
        print("[排程] 無持倉，跳過出場掃描")
        _reschedule(interval)
        return

    print(f"[排程] 出場掃描開始 ({datetime.now().strftime('%H:%M:%S')})")

    # 避免循環匯入：動態載入
    from modules.market_data import get_latest_price

    for symbol, pos in list(_positions_ref.items()):
        latest_price = get_latest_price(symbol)
        if latest_price is not None:
            check_exit_and_notify(symbol, latest_price)

    _reschedule(interval)

def _reschedule(interval: int):
    threading.Timer(interval, schedule_exit_check, kwargs={"interval": interval}).start()

