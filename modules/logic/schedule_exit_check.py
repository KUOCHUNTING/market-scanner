import threading
from datetime import datetime
from modules.logic.should_exit import should_exit
from modules.logic.execute_exit import execute_exit
from modules.market_data import get_latest_price  # ← 你應該已經有這個模組
from modules.config import capital_left, positions

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

        # ✅ 判斷是否該出場
        latest_price = get_latest_price(symbol)
        if latest_price is None:
            print(f"[⚠️ 無法取得價格] {symbol} ➜ 跳過")
            continue

        should_exit_flag, reason = should_exit(symbol, pos, latest_price)
        if should_exit_flag:
            execute_exit(symbol, pos, latest_price, reason)
        else:
            entry_price = pos.get("entry_price")
            if entry_price:
                return_rate = (latest_price - entry_price) / entry_price * 100 if "多" in pos["direction"] else (entry_price - latest_price) / entry_price * 100
                pnl_text = f"{'🟢' if return_rate > 0 else '🔴' if return_rate < 0 else '⚪'} 目前價：{latest_price:.2f}｜報酬率：{return_rate:+.2f}%"
            else:
                pnl_text = "❓ 無法計算報酬率"

            strategy = pos.get("strategy", "未知策略")
            holding_minutes = int((datetime.now() - entry_time).total_seconds() / 60)
            print(f"✅【持續持有】{symbol} 尚未觸發出場條件 {pnl_text}｜策略={strategy}｜已持有 {holding_minutes} 分鐘")

    # ✅ 每 10 秒重新排程
    threading.Timer(10, schedule_exit_check).start()
