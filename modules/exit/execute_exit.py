# modules/exit/execute_exit.py
from datetime import datetime
from modules.utils.gsheet_writer import write_exit_to_sheet
from modules.notify.discord_push import send_discord_message
from modules.config.config import WEBHOOK_URL
from modules.notify.build_discord_message import build_exit_message  # ✅ 使用格式化訊息
import os
from dotenv import load_dotenv
load_dotenv()
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

def execute_exit(symbol, entry_time, exit_price, entry_price,
                 rsi=None, zscore=None, roc=None, obv=None,
                 vwap=None, ema5=None, ema20=None,
                 strategy_name="未標記策略",
                 shares=1, reason="達到出場條件"):  # ✅ 加入 shares 與 reason

    now_dt = datetime.now()
    now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")

    holding_minutes = compute_holding_minutes(entry_time, now_dt)
    direction = "做多" if entry_price <= exit_price else "做空"

    if entry_price == 0:
        return_pct = 0
    else:
        return_pct = (
            (exit_price - entry_price) / entry_price
            if direction == "做多"
            else (entry_price - exit_price) / entry_price
        )
    pnl = (exit_price - entry_price) * shares if direction == "做多" else (entry_price - exit_price) * shares

    # ✅ 寫入出場紀錄
    try:
        write_exit_to_sheet({
            "symbol": symbol,
            "entry_time": entry_time,
            "exit_time": now_dt,
            "return_rate": f"{round(return_pct * 100, 2)}%" if isinstance(return_pct, (int, float)) else "",
            "pnl": pnl,
            "holding_minutes": holding_minutes,
            "exit_price": exit_price,
            "rsi": rsi,
            "zscore": zscore,
            "roc": roc,
            "obv": obv,
            "vwap": vwap,
            "ema5": ema5,
            "ema20": ema20,
            "strategy_name": strategy_name,
            "shares": shares,
            "reason": reason,
            "direction": direction  # ✅ 建議補上
        })
    except Exception as e:
        print(f"[❌ 寫入 Google Sheets 失敗] {symbol} ➜ {e}")

    # ✅ Discord 推播
    message = build_exit_message(
        symbol=symbol,
        direction=direction,
        entry_price=entry_price,
        exit_price=exit_price,
        return_rate=return_pct,
        shares=shares,
        reason=reason,
        strategy_name=strategy_name
    )
    send_discord_message(WEBHOOK_URL, message)

def compute_holding_minutes(entry_time, exit_time_dt):
    if isinstance(entry_time, str):
        entry_time = datetime.strptime(entry_time, "%Y-%m-%d %H:%M:%S")
    delta = exit_time_dt - entry_time
    return int(delta.total_seconds() // 60)
