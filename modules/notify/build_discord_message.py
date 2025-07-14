from modules.utils.format import safe_float

def build_entry_message(symbol, price, strategy_name, direction,
                        confidence_score=None, score=None,
                        rsi=None, zscore=None,
                        ema5=None, ema20=None,
                        bb_upper=None, bb_lower=None, obv=None,
                        strategy_type=None, signal_type=None,
                        trend_score=None, rrov_score=None, mean_score=None,
                        signal_note="", shares=None, capital_used=None, capital_left=None,
                        trend_text=None, trend_emoji=None,
                        up_count=None, down_count=None,
                        ema_trend=None):

    # 🧾 安全格式處理
    price_str = safe_float(price, 2, prefix="$")
    rsi_str = safe_float(rsi, 1)
    zscore_str = safe_float(zscore, 2)
    ema5_str = safe_float(ema5, 2)
    ema20_str = safe_float(ema20, 2)
    bb_upper_str = safe_float(bb_upper, 2)
    bb_lower_str = safe_float(bb_lower, 2)
    obv_str = f"{int(obv)}" if obv is not None else "N/A"
    confidence_str = safe_float(confidence_score)
    score_str = safe_float(score)

    # 🧭 標題
    direction_label = "多單" if direction == "多" else "空單"
    signal_type_label = f"【{direction_label} 技術策略 訊號】{symbol}"

    # 📦 建立訊息內容
    message = f"{signal_type_label}\n"
    message += f"📌 類型：{strategy_type or '未分類'}（方向：{direction}）\n"
    message += f"📉 收盤價：{price_str}｜RSI：{rsi_str}｜Z-score：{zscore_str}\n"
    message += f"📈 EMA5：{ema5_str}｜EMA20：{ema20_str}\n"
    message += f"🎯 布林通道上：{bb_upper_str}｜下：{bb_lower_str}\n"
    message += f"🔄 OBV：{obv_str}\n\n"

    message += f"📊 命中率 ➜ 順勢：{(trend_score or 0) * 100:.2f}%｜RROV：{(rrov_score or 0) * 100:.2f}%｜均值：{(mean_score or 0) * 100:.2f}%\n"
    message += f"🧠 技術信心：{confidence_str}｜策略分數：{score_str}\n"

    if trend_text:
        message += f"\n📊 趨勢摘要：{trend_text} {trend_emoji or ''}\n"

    if ema_trend:
        message += f"📈 均線排列：{ema_trend}\n"

    if up_count is not None and down_count is not None:
        message += f"📊 近10根K線：上漲 {up_count} 根｜下跌 {down_count} 根\n"

    message += f"\n📋 訊號摘要：{signal_note}\n"
    message += f"🧠 策略名稱：{strategy_name}\n\n"
    message += f"📦 股數：{shares if shares is not None else 0} 股｜💰 進場資金：{safe_float(capital_used, 0, prefix='$')}\n"
    message += f"💼 剩餘資金：{safe_float(capital_left, 0, prefix='$')}"

    return message

# ✅ 擠壓策略推播訊息（多空雙向皆可）
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
