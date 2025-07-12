# modules/build_discord_message.py

def build_entry_message(symbol, direction, strategy_name, score,
                        rrov_score, trend_score, mean_score,
                        latest_price, rsi, zscore,
                        signal_note, confidence_score,
                        shares, capital_used, capital_left,
                        macd=None, tmo=None, ema_trend=None, up_count=None, down_count=None):
    
    direction_emoji = "🟢 多單" if direction == "多" else "🔴 空單"
    trend_emoji = "📈" if ema_trend == "多" else "📉" if ema_trend == "空" else "⚪"
    trend_text = ema_trend or "無方向"

    message = f"🚀【{direction_emoji} 技術策略 訊號】{symbol}\n"
    message += f"📌 類型：{direction.upper()}（方向：{direction}）\n"
    message += f"🎯 命中率 ➜ 順勢：{trend_score:.2f}｜RROV：{rrov_score:.2f}｜均值：{mean_score:.2f}\n"
    message += f"🧠 技術信心：{confidence_score:.2f}\n"
    message += f"📈 收盤價：${latest_price:.2f}｜RSI：{rsi:.1f}｜Z-score：{zscore:.2f}\n"
    
    if macd is not None:
        message += f"📉 MACD：{macd:.2f}｜"
    if tmo is not None:
        message += f"TMO：{tmo:.2f}\n"

    message += f"📋 訊號摘要：{signal_note}\n"
    message += f"📊 策略名稱：{strategy_name}\n"
    
    if up_count is not None and down_count is not None:
        message += f"{trend_emoji} EMA 趨勢：上漲 {up_count} 次｜下跌 {down_count} 次（偏 {trend_text}）\n"

    message += f"📦 股數：{shares} 股｜💰 進場資金：${capital_used:.0f}｜剩餘資金：${capital_left:,.0f}"

    return message
