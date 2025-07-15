from datetime import datetime
from modules.utils.connect_to_gsheet import connect_to_gsheet, write_exit_to_sheet
from modules.notify.discord_push import send_discord_message
from modules.config.config import WEBHOOK_URL
from modules.utils.format import safe_float

# === 📦 出場執行模組 ===
def execute_exit(symbol, entry_time, exit_price, entry_price, rsi=None, zscore=None,
                 roc=None, obv=None, vwap=None, ema5=None, ema20=None, strategy_name="未標記策略"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    holding_time = compute_holding_time(entry_time, now)

    direction = "做多" if entry_price <= exit_price else "做空"
    return_pct = (exit_price - entry_price) / entry_price * 100 if direction == "做多" else (entry_price - exit_price) / entry_price * 100
    pnl = (exit_price - entry_price) if direction == "做多" else (entry_price - exit_price)

    # === 📝 寫入 Google Sheets ===
    row = [
        symbol,
        entry_time,
        now,
        round(return_pct, 2),
        round(pnl, 2),
        holding_time,
        round(exit_price, 2),
        safe_float(rsi),
        safe_float(zscore),
        safe_float(roc),
        safe_float(obv),
        safe_float(vwap),
        safe_float(ema5),
        safe_float(ema20),
        strategy_name
    ]
    write_exit_to_sheet(row)

    # === 📣 Discord 推播 ===
    message = (
        f"📤 **出場通知** `{symbol}`\n"
        f"▶️ 策略：{strategy_name}｜方向：{direction}\n"
        f"💰 進場：{entry_price:.2f} ➜ 出場：{exit_price:.2f}\n"
        f"📊 報酬率：{return_pct:.2f}%｜損益：${pnl:.2f}\n"
        f"⏱️ 持倉時間：{holding_time}\n"
        f"📅 出場時間：{now}"
    )
    send_discord_message(WEBHOOK_URL, message)

# === ⏱️ 計算持倉時間 ===
def compute_holding_time(entry_time_str, exit_time_str):
    fmt = "%Y-%m-%d %H:%M:%S"
    try:
        entry_time = datetime.strptime(entry_time_str, fmt)
        exit_time = datetime.strptime(exit_time_str, fmt)
        delta = exit_time - entry_time
        hours, remainder = divmod(delta.total_seconds(), 3600)
        minutes, _ = divmod(remainder, 60)
        return f"{int(hours)} 小時 {int(minutes)} 分鐘"
    except Exception:
        return "N/A"
