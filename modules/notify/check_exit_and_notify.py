# 📂 modules/notify/check_exit_and_notify.py

from datetime import datetime, timedelta
from modules.notify.discord_push import send_discord_message
from modules.exit_position import exit_position
from modules.config import (
    DEFAULT_STOP_LOSS,
    DEFAULT_TAKE_PROFIT,
    TRAIL_TRIGGER,
    TRAIL_MARGIN,
    WEBHOOK_URL
)
from modules.repair_position import repair_position  # ✅ 建議移出 logic 資料夾

# ⛔ 全域變數應由主程式傳進來或用 Singleton 管理
positions = {}
capital_left = 0
last_tracking_push_time = {}

def check_exit_and_notify(symbol, latest_price):
    global capital_left

    if symbol not in positions:
        return

    # ✅ 修補持倉資料
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

    # ✅ 停損與鎖利條件
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

    # ✅ 3 分鐘一次追蹤推播
    if reason is None or exit_ratio <= 0:
        now = datetime.now()
        last_push = last_tracking_push_time.get(symbol)
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
            last_tracking_push_time[symbol] = now
        return

    # ✅ 出場處理
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

    strategy_name_map = {
        "均值回歸": "🎯 均值回歸策略",
        "順勢策略": "🔥 順勢策略",
        "RROV": "📊 RROV 策略"
    }
    strategy_name = strategy_name_map.get(strategy, f"📌 {strategy}")

    content = (
        f"{emoji} **[出場通知 - {strategy_name}｜{direction}單]** {symbol}\n"
        f"📈 出場價格：${latest_price:.2f} ｜ 數量：{exit_qty} 股\n"
        f"📊 報酬率：{return_rate:.2f}% ｜ 獲利金額：${profit_dollar:.2f}\n"
        f"🔄 原因：{reason}\n"
        f"🕒 時間：{time_str}"
    )
    send_discord_message(WEBHOOK_URL, content)
    print(content)

    # ✅ 紀錄出場
    exit_position(symbol, latest_price, pos)

    if pos["quantity"] <= 0:
        del positions[symbol]

import threading
from modules.logic.should_exit import should_exit  # ← 你要實作
from modules.logic.execute_exit import execute_exit  # ← 你要實作
from modules.market_data import get_latest_price     # ← 你要實作

def schedule_exit_check():
    if not positions:
        print("[排程] 無持倉，跳過出場檢查")
        threading.Timer(10, schedule_exit_check).start()
        return

    print(f"[排程] 執行出場掃描...")

    for symbol, pos in positions.items():
        quantity = pos.get("quantity", 0)

        if quantity <= 0:
            print(f"[略過出場] {symbol} ➜ 無持倉")
            continue

        entry_time = pos.get("entry_time")
        if entry_time:
            elapsed_seconds = (datetime.now() - entry_time).total_seconds()
            if elapsed_seconds < 30:
                print(f"[⏳ 冷卻中] {symbol} ➜ 建倉未滿 30 秒（{elapsed_seconds:.1f}s），略過出場判斷")
                continue

        if should_exit(symbol):
            execute_exit(symbol)
        else:
            latest_price = get_latest_price(symbol)
            entry_price = pos.get("entry_price")
            return_rate = None
            if latest_price and entry_price and entry_price > 0:
                return_rate = ((latest_price - entry_price) / entry_price) * 100
                if return_rate > 10:
                    emoji = "🟢"
                elif return_rate < -5:
                    emoji = "🔴"
                else:
                    emoji = "⚪"
                pnl_text = f"{emoji} 目前價：{latest_price:.2f}｜報酬率：{return_rate:+.2f}%"
            else:
                pnl_text = "❓ 無法計算報酬率"

            strategy = pos.get("strategy", "未知策略")
            holding_minutes = int((datetime.now() - entry_time).total_seconds() / 60) if entry_time else 0
            print(f"✅【持續持有】{symbol} 尚未觸發出場條件 {pnl_text}｜策略={strategy}｜已持有 {holding_minutes} 分鐘")

    threading.Timer(10, schedule_exit_check).start()

