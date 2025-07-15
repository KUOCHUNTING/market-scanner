from datetime import datetime
from modules.notify.discord_push import send_discord_message
from modules.connect_to_gsheet import write_exit_to_sheet
from modules.indicator_cache import get_cached_indicators

def execute_exit(symbol, position, current_price, reason):
    entry_price = position["entry_price"]
    entry_time = position["entry_time"]
    direction = position["direction"]
    strategy_name = position.get("strategy", "未標記策略")
    confidence_score = position.get("confidence_score")
    quantity = position["quantity"]

    # 報酬率與損益
    return_rate = (current_price - entry_price) / entry_price if "多" in direction else (entry_price - current_price) / entry_price
    pnl = round(return_rate * entry_price * quantity, 2)
    return_rate = round(return_rate, 4)
    holding_minutes = int((datetime.now() - entry_time).total_seconds() / 60)

    # 指標讀取（從 cache 抓）
    indicators = get_cached_indicators(symbol)
    def safe_get(key): return indicators.get(key, [None])[-1]

    rsi = safe_get("rsi")
    zscore = safe_get("zscore")
    roc = safe_get("roc")
    obv = safe_get("obv")
    vwap = safe_get("vwap")
    ema5 = safe_get("ema_5")
    ema20 = safe_get("ema_20")

    # 推播訊息
    emoji = "✅" if return_rate >= 0 else "⚠️"
    message = (
        f"{emoji} **[出場通知｜{strategy_name}]** `{symbol}`\n"
        f"📈 出場價：${current_price:.2f}｜方向：{direction}\n"
        f"📊 報酬率：{return_rate*100:.2f}%｜損益：${pnl:.2f}\n"
        f"⏱️ 持倉時間：{holding_minutes} 分鐘\n"
        f"📌 原因：{reason}"
    )
    send_discord_message(message)

    # ✅ 寫入 Google Sheets
    write_exit_to_sheet(
        symbol=symbol,
        entry_time=entry_time,
        exit_time=datetime.now(),
        return_rate=return_rate,
        pnl=pnl,
        holding_minutes=holding_minutes,
        exit_price=current_price,
        rsi=rsi,
        zscore=zscore,
        roc=roc,
        obv=obv,
        vwap=vwap,
        strategy_name=strategy_name,
        confidence_score=confidence_score
    )
