import threading
from datetime import datetime

from modules.config import DEFAULT_STOP_LOSS, DEFAULT_TAKE_PROFIT, TRAIL_TRIGGER, TRAIL_MARGIN
from modules.notify.discord_push import send_discord_message
from modules.market_data import get_latest_price
from modules.logic.execute_exit import execute_exit

# 全域持倉 dict
positions = {}
capital_left = 0
last_tracking_push_time = {}

def schedule_exit_check():
    if not positions:
        print("[排程] 無持倉，跳過出場檢查")
        threading.Timer(10, schedule_exit_check).start()
        return

    print("[排程] 執行出場掃描...")
    for symbol, pos in positions.items():
        if pos.get("quantity", 0) <= 0:
            continue

        entry_price = pos["entry_price"]
        direction = pos["direction"]
        sell_stage = pos.get("sell_stage", 0)
        max_gain = pos.get("max_gain", 0)
        entry_time = pos.get("entry_time")

        latest_price = get_latest_price(symbol)
        if not latest_price:
            print(f"[❌ 價格錯誤] 無法取得 {symbol} 的現價")
            continue

        # ➤ 計算報酬率
        if "多" in direction:
            return_rate = (latest_price - entry_price) / entry_price * 100
        elif "空" in direction:
            return_rate = (entry_price - latest_price) / entry_price * 100
        else:
            return_rate = 0

        # ➤ 更新最高報酬
        if return_rate > max_gain:
            pos["max_gain"] = return_rate
            max_gain = return_rate

        # ➤ 出場判斷條件
        reason, trigger_exit = None, False
        if return_rate <= -DEFAULT_STOP_LOSS:
            reason = f"🛑 停損觸發：{return_rate:.2f}%"
            trigger_exit = True
        elif return_rate >= DEFAULT_TAKE_PROFIT and sell_stage == 0:
            reason = f"🔒 第一段鎖利：{return_rate:.2f}%"
            pos["sell_stage"] = 1
            trigger_exit = True
        elif return_rate >= 8.0 and sell_stage <= 1:
            reason = f"🔒 第二段鎖利：{return_rate:.2f}%"
            pos["sell_stage"] = 2
            trigger_exit = True
        elif max_gain >= TRAIL_TRIGGER and (max_gain - return_rate) >= TRAIL_MARGIN and sell_stage <= 1:
            drop = round(max_gain - return_rate, 2)
            reason = f"🔃 追蹤停利觸發（回落 {drop:.2f}%）"
            pos["sell_stage"] = 3
            trigger_exit = True

        # ➤ 出場執行
        if trigger_exit:
            execute_exit(symbol, pos, latest_price, reason)
            if pos["quantity"] <= 0:
                del positions[symbol]
        else:
            now = datetime.now()
            last_push = last_tracking_push_time.get(symbol)
            if not last_push or (now - last_push).total_seconds() >= 180:
                holding_minutes = int((now - entry_time).total_seconds() / 60) if entry_time else 0
                emoji = "🟢" if return_rate > 0 else "🔴" if return_rate < 0 else "⚪"
                message = (
                    f"🔔【追蹤持倉】{symbol} {emoji}\n"
                    f"📈 價格：{latest_price:.2f} ➜ 報酬率：{return_rate:+.2f}%\n"
                    f"策略：{pos.get('strategy')}｜持倉：{holding_minutes} 分鐘"
                )
                send_discord_message(message)
                last_tracking_push_time[symbol] = now

    threading.Timer(10, schedule_exit_check).start()
