from datetime import datetime
from modules.notify.discord_push import send_discord_message
from modules.connect_to_gsheet import write_exit_to_sheet

def execute_exit(symbol, position, current_price, indicators, reason="策略觸發出場"):
    try:
        now = datetime.now()
        entry_price = position["entry_price"]
        direction = position["direction"]
        shares = position["shares"]
        entry_time = position["entry_time"]

        # === 📊 計算損益與報酬率 ===
        if direction == "做多":
            pnl = (current_price - entry_price) * shares
            return_pct = (current_price - entry_price) / entry_price * 100
        else:  # 做空
            pnl = (entry_price - current_price) * shares
            return_pct = (entry_price - current_price) / entry_price * 100

        # === 📩 推播格式 ===
        msg = f"📤 出場通知｜{symbol}\n"
        msg += f"📈 建倉價：{entry_price:.2f} ➜ 出場價：{current_price:.2f}\n"
        msg += f"🎯 方向：{direction}｜策略：{position.get('strategy_name', '未標記')}\n"
        msg += f"💰 報酬率：{return_pct:.2f}%｜損益：${pnl:.2f}\n"
        msg += f"⏳ 持倉時間：{str(now - entry_time)}｜出場原因：{reason}"

        send_discord_message(msg)

        # === ✅ 寫入 Google Sheets 出場紀錄 ===
        write_exit_to_sheet(
            symbol=symbol,
            entry_time=entry_time,
            exit_time=now,
            return_rate=return_pct,
            pnl=pnl,
            holding_time_str=str(now - entry_time),
            exit_price=current_price,
            rsi=indicators.get("rsi", [None])[-1],
            zscore=indicators.get("zscore", [None])[-1],
            roc=indicators.get("roc", [None])[-1],
            obv=indicators.get("obv", [None])[-1],
            vwap=indicators.get("vwap", [None])[-1],
            ema5=indicators.get("ema_5", [None])[-1],
            ema20=indicators.get("ema_20", [None])[-1],
            strategy_name=position.get("strategy_name", "未標記策略")
        )

    except Exception as e:
        print(f"❌ [出場錯誤] {symbol} ➜ {e}")
