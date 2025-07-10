def push_exit_to_discord(symbol, direction, entry_price, exit_price, return_rate, shares, reason):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    strategy = positions[symbol].get("strategy", "未標記策略")

    if strategy == '均值回歸':
        strategy_label = "🎯 均值回歸策略"
    elif strategy == '順勢策略':
        strategy_label = "🔥 順勢策略"
    else:
        strategy_label = "📊 RROV 策略"

    emoji = "🐸" if direction == "多" else "🐶"

    msg = f"""{emoji} **[出場 - {direction}單]** {symbol}
📌 策略：{strategy_label}
💵 出場價格：${exit_price:.2f}｜進場價格：${entry_price:.2f}
📊 報酬率：{return_rate:.2%}｜股數：{shares}
🔄 出場原因：{reason}
🕒 時間：{now}"""

    try:
        requests.post(WEBHOOK_URL, json={"content": msg})
    except Exception as e:
        print(f"[EXCEPTION] 出場推播錯誤：{e}")


import requests