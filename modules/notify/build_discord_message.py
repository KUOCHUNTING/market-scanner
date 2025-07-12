# modules/notify/build_discord_message.py
def build_entry_message(symbol, strategy_type, signal_type, direction,
                        score, win_rate, trend_emoji, trend_text,
                        up_count, down_count, ema_trend, signal_note,
                        strategy_name, shares, capital_used, capital_left):
    message  = f"🚀【{strategy_type} 訊號】{symbol}\n\n"
    message += f"📊 類型：{signal_type}（方向：{direction}）\n"
    message += f"🧠 信心分數：{score:.2f}｜RROV 命中率：{win_rate:.2f}%\n\n"
    message += f"📈 技術傾向：{trend_emoji} 技術偏{trend_text}\n"
    message += f"📉 EMA 趨勢：上漲 {up_count} 次｜下跌 {down_count} 次（偏{ema_trend}）\n\n"
    message += f"📋 訊號說明：\n{signal_note}\n\n"
    message += f"🧠 策略：{strategy_name}\n\n"
    message += f"📦 股數：{shares} 股\n"
    message += f"💰 進場資金：${int(capital_used):,}\n"
    message += f"💼 剩餘資金：${int(capital_left):,}"
    return message
