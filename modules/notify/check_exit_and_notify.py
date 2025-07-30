from datetime import datetime, timedelta
import threading
import os
from dotenv import load_dotenv

from modules.utils.price_fetcher import get_latest_price
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

load_dotenv()
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
last_tracking_push_time = {}

# ✅ 出場與追蹤通知主邏輯（傳入單筆持倉 pos）
def check_exit_and_notify(symbol, latest_price, pos):
    entry_price = pos["entry_price"]
    direction = pos["direction"]
    capital_used = pos["capital_used"]
    quantity = pos["quantity"]
    sell_stage = pos.get("sell_stage", 0)
    max_gain = pos.get("max_gain", 0.0)
    strategy = pos.get("strategy_name", "未命名")
    entry_time = pos.get("entry_time")

    # ✅ 計算報酬率
    if "多" in direction:
        return_rate = (latest_price - entry_price) / entry_price
    elif "空" in direction:
        return_rate = (entry_price - latest_price) / entry_price
    else:
        print(f"[⚠️方向異常] direction={direction!r}")
        return

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

    # ✅ 尚未出場 → 每 3 分鐘推播一次追蹤
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
            send_discord_message(message, webhook_url=WEBHOOK_URL)
            print(message)
            last_tracking_push_time[symbol] = now
        return

    # ✅ 出場處理
    exit_qty = int(quantity * exit_ratio)
    if exit_qty <= 0:
        print(f"[略過] {symbol} ➜ 出場數量為 0")
        return

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
        strategy_name=strategy,
        shares=exit_qty,
        reason=reason
    )

    # ✅ 更新持倉狀態（主控程式可選擇是否刪除）
    pos["quantity"] -= exit_qty
    pos["sell_stage"] = sell_stage


# === 出場排程 ===

_positions_ref = None

def set_positions_ref(pos_list):
    global _positions_ref
    _positions_ref = pos_list

def schedule_exit_check(interval: int = 10):
    print("🟡 [DEBUG] ✅ schedule_exit_check() 被呼叫了")

    if not _positions_ref:
        print("🟥 [排程] 無持倉 ➜ 跳過出場掃描")
        _reschedule(interval)
        return

    print(f"🟢 [排程] 出場掃描開始 ➜ 共 {len(_positions_ref)} 檔")

    for pos in _positions_ref:
        symbol = pos.get("symbol")
        if not symbol:
            continue
        price, ts_str = get_latest_price(symbol)
        if price is not None:
            print(f"🟢 [DEBUG] {symbol} 最新價格：{price}（{ts_str}）")
            check_exit_and_notify(symbol, price, pos)
        else:
            print(f"🟠 [跳過] 無法取得 {symbol} 價格 ➜ 不執行出場判斷")

    _reschedule(interval)

def _reschedule(interval: int):
    threading.Timer(interval, schedule_exit_check, kwargs={"interval": interval}).start()
