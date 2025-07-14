 from modules.utils.format import safe_float

# ✅ 建倉訊息組裝
def build_entry_message(symbol, price, strategy_type, signal_type, strategy_name,
                        signal_note, direction, score=None, confidence_score=None,
                        rsi=None, zscore=None, ema5=None, ema20=None,
                        bb_upper=None, bb_lower=None, obv=None,
                        trend_score=None, rrov_score=None, mean_score=None,
                        shares=None, capital_used=None, capital_left=None):
    # === 🎯 標題區 ===
    message = f"📌 {direction} 技術策略 ➤ `{symbol}`\n"
    message += f"🔖 類型：{strategy_type}\n"
    message += f"📈 收盤價：{safe_float(price, 2, prefix='$')}"
    if rsi is not None:     message += f" | RSI：{safe_float(rsi)}"
    if zscore is not None:  message += f" | Z-score：{safe_float(zscore)}"
    message += "\n"

    # === 📊 技術摘要 ===
    message += f"🧠 訊號摘要：{signal_note}\n"
    message += f"🎯 策略名稱：{strategy_name}\n"

    if ema5 is not None and ema20 is not None:
        message += f"📏 EMA5：{safe_float(ema5)}｜EMA20：{safe_float(ema20)}\n"
    if bb_upper is not None and bb_lower is not None:
        message += f"📊 布林通道：上={safe_float(bb_upper)}｜下={safe_float(bb_lower)}\n"
    if obv is not None:
        message += f"📶 OBV：{safe_float(obv)}\n"

    # === 📉 命中率區（只顯示觸發策略）
    triggered_score = None
    if signal_type == "trend":
        triggered_score = trend_score
    elif signal_type == "rrov":
        triggered_score = rrov_score
    elif signal_type == "mean":
        triggered_score = mean_score
    if triggered_score is not None:
        message += f"📊 命中率 ➤ {strategy_name}：{safe_float(triggered_score * 100, 2, suffix='%')}\n"

    # === 🧠 信心與策略分數 ===
    if confidence_score is not None:
        message += f"🧠 技術信心：{safe_float(confidence_score)}｜策略分數：{safe_float(score)}\n"

    # === 🧾 建倉資訊 ===
    if shares is not None and capital_used is not None:
        message += f"📦 股數：{shares} 股｜💰 進場資金：{safe_float(capital_used, 2, prefix='$')}\n"
    if capital_left is not None:
        message += f"📤 剩餘資金：{safe_float(capital_left, 2, prefix='$')}\n"

    return message


# ✅ 擠壓策略訊息
def build_breakout_message(result):
    from modules.utils.format import safe_float

    symbol = result.get("symbol", "未知代號")
    direction = result.get("direction", "未知方向")
    score = result.get("score", 0)
    conditions = result.get("conditions_met", [])
    close = result.get("close", None)
    rsi = result.get("rsi", None)
    ema_5 = result.get("ema_5", None)
    ema_20 = result.get("ema_20", None)
    strategy_name = result.get("strategy_name", "擠壓策略")

    emoji = "🚀" if direction == "做多" else "💥"

    message  = f"{emoji}【擠壓策略觸發】{symbol}｜{strategy_name}\n\n"
    message += f"📌 收盤價：{safe_float(close, 2, prefix='$')}｜RSI：{safe_float(rsi, 1)}\n"
    message += f"📈 EMA5：{safe_float(ema_5)}｜EMA20：{safe_float(ema_20)}\n"
    message += f"🎯 命中條件（{score}）項：\n"
    message += "\n".join([f"- {c}" for c in conditions]) + "\n\n"
    message += f"📊 判定方向：{direction}"

    return message
