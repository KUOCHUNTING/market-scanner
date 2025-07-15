from modules.notify.discord_push import send_discord_message
from modules.connect_to_gsheet import write_exit_to_sheet

def execute_exit(symbol, position, current_price, reason):
    entry_price = position["entry_price"]
    direction = position["direction"]

    # 計算報酬率（多空方向支援）
    if direction == "做多":
        return_pct = (current_price - entry_price) / entry_price * 100
    else:  # 做空
        return_pct = (entry_price - current_price) / entry_price * 100

    # 建立推播訊息
    message = f"📤 出場通知｜{symbol}\n"
    message += f"💰 建倉價：${entry_price:.2f} ➜ 現價：${current_price:.2f}\n"
    message += f"📈 報酬率：{return_pct:.2f}%｜方向：{direction}\n"
    message += f"📌 原因：{reason}"

    # 推播到 Discord
    send_discord_message(message)

    # 寫入 Google Sheets
    write_exit_to_sheet(symbol, current_price, reason, position, indicators)
