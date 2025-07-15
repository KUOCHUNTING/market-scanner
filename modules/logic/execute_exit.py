from modules.notify.discord_push import send_discord_message
from modules.connect_to_gsheet import write_exit_to_sheet

def execute_exit(symbol, position, current_price, reason):
    message = f"📤 出場通知｜{symbol}\n"
    message += f"💰 建倉價：{position['entry_price']:.2f} ➜ 現價：{current_price:.2f}\n"
    message += f"📊 方向：{position['direction']}｜原因：{reason}"

    # 推播
    send_discord_message(message)

    # 寫入紀錄
    write_exit_to_sheet(symbol, current_price, reason)
