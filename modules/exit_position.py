from datetime import datetime
from modules.notify.discord_push import send_discord_message
from modules.connect_to_gsheet import write_exit_to_sheet

def check_exit_condition(position, current_price):
    """
    出場判斷邏輯（鎖利 & 停損）
    三段鎖利條件：
    - +5%、+10%、+15% 分別觸發不同條件
    停損條件：
    - 跌破 -3% 強制出場
    """
    entry_price = position["entry_price"]
    direction = position["direction"]
    gain = (current_price - entry_price) / entry_price if direction == "做多" else (entry_price - current_price) / entry_price

    if gain <= -0.03:
        return True, "🔻 停損出場（-3%）"
    elif gain >= 0.15:
        return True, "💰 第三段鎖利（+15%）"
    elif gain >= 0.10:
        return True, "💰 第二段鎖利（+10%）"
    elif gain >= 0.05:
        return True, "💰 第一段鎖利（+5%）"
    return False, None

def execute_exit(symbol, position, current_price, indicators, reason="策略觸發出場"):
    """
    出場處理流程：
    1. 推播 Discord
    2. 計算報酬率、損益、持倉時間
    3. 寫入 Google Sheets
    """
    entry_price = position["entry_price"]
    direction = position["direction"]
    shares = position["shares"]
    entry_time = position.get("entry_time")
    strategy_name = position.get("strategy_name", "未標記策略")
    confidence_score = position.get("confidence_score")

    # 計算報酬與損益
    return_rate = (current_price - entry_price) / entry_price if direction == "做多" else (entry_price - current_price) / entry_price
    pnl = return_rate * entry_price * shares

    # 計算持倉時間（分鐘）
    if entry_time:
        holding_minutes = int((datetime.now() - entry_time).total_seconds() // 60)
    else:
        holding_minutes = None

    # 構建訊息
    message = f"📤 出場通知｜`{symbol}`\n"
    message += f"📈 出場價：${current_price:.2f}（{reason}）\n"
    message += f"📉 報酬率：{return_rate:.2%}｜損益：${pnl:.2f}\n"
    message += f"⏱️ 持倉時間：{holding_minutes} 分鐘｜方向：{direction}｜策略：{strategy_name}"

    send_discord_message(message)

    # 指標資料
    rsi = indicators.get("rsi").iloc[-1] if indicators.get("rsi") is not None else None
    zscore = indicators.get("zscore").iloc[-1] if indicators.get("zscore") is not None else None
    roc = indicators.get("roc").iloc[-1] if indicators.get("roc") is not None else None
    obv = indicators.get("obv").iloc[-1] if indicators.get("obv") is not None else None
    vwap = indicators.get("vwap").iloc[-1] if indicators.get("vwap") is not None else None
    ema5 = indicators.get("ema_5").iloc[-1] if indicators.get("ema_5") is not None else None
    ema20 = indicators.get("ema_20").iloc[-1] if indicators.get("ema_20") is not None else None

    # 寫入 Google Sheets
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
