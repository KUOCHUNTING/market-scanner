# modules/build_discord_message.py
def build_entry_message(symbol, direction, strategy_name, score,
                        rrov_score, trend_score, mean_score,
                        latest_price, rsi, zscore,
                        signal_note, confidence_score,
                        shares, capital_used, capital_left):
    direction_emoji = "🟢 多單" if direction == "多" else "🔴 空單"

    message = f"🚀【{direction_emoji} 技術選股 訊號】{symbol}\n"
    message += f"📌 類型：{direction.upper()}（方向：{'多' if direction == '多' else '空'}）\n"
    message += f"🎯 命中率 ➜ 順勢：{trend_score:.2f}｜RROV：{rrov_score:.2f}｜均值：{mean_score:.2f}\n"
    message += f"🧠 技術信心：{confidence_score:.2f}\n"
    message += f"📈 收盤價：${latest_price:.2f}｜RSI：{rsi:.1f}｜Z-score：{zscore:.2f}\n"
    message += f"📉 技術摘要：{signal_note}\n"
    message += f"📊 策略：{strategy_name}\n"
    message += f"📦 股數：{shares} 股｜進場資金：${capital_used:.0f}｜剩餘資金：${capital_left:,.0f}"

    return message
