from datetime import datetime
from modules.config import positions, capital_left
from modules.notify.discord_push import send_discord_message
from modules.connect_to_gsheet import write_exit_to_sheet

def execute_exit(symbol):
    pos = positions[symbol]
    latest_price = pos["latest_price"]
    direction = pos["direction"]
    entry_price = pos["entry_price"]
    entry_time = pos["entry_time"]
    quantity = pos["quantity"]
    exit_ratio = pos.get("exit_ratio", 1.0)
    reason = pos.get("exit_reason", "未提供原因")
    strategy_name = pos.get("strategy", "未標記")

    exit_qty = int(quantity * exit_ratio)
    if exit_qty <= 0:
        return

    # 計算損益
    pnl = (latest_price - entry_price) if "多" in direction else (entry_price - latest_price)
    profit = pnl * exit_qty
    return_rate = (pnl / entry_price) * 100
    holding_minutes = int((datetime.now() - entry_time).total_seconds() / 60)

    # 推播
    emoji = "✅" if return_rate >= 0 else "⚠️"
    msg = (
        f"{emoji} **[出場通知｜{strategy_name}｜{direction}]** {symbol}\n"
        f"📈 出場價格：${latest_price:.2f}｜數量：{exit_qty}\n"
        f"📊 報酬率：{return_rate:.2f}%｜損益：${profit:.2f}\n"
        f"🔄 原因：{reason}｜持倉：{holding_minutes} 分鐘"
    )
    send_discord_message(msg)

    # Sheets 寫入
    from modules.indicator_cache import indicator_cache
    indicators = indicator_cache.get(symbol, {})  # 可補技術指標

    write_exit_to_sheet(
        symbol=symbol,
        entry_time=entry_time,
        exit_time=datetime.now(),
        return_rate=return_rate / 100,
        pnl=profit,
        holding_minutes=holding_minutes,
        exit_price=latest_price,
        rsi=indicators.get("rsi"),
        zscore=indicators.get("zscore"),
        roc=indicators.get("roc"),
        obv=indicators.get("obv"),
        vwap=indicators.get("vwap"),
        strategy_name=strategy_name
    )

    # 更新持倉與資金
    pos["quantity"] -= exit_qty
    capital_left += latest_price * exit_qty

    if pos["quantity"] <= 0:
        del positions[symbol]
