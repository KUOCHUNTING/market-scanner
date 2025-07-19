# modules/exit/schedule_exit_check.py

from modules.exit.should_exit import should_exit
from modules.exit.execute_exit import execute_exit
from modules.entry.positions import positions

def schedule_exit_check():
    to_exit = []

    for symbol, pos in positions.items():
        entry_price = pos.get("entry_price")
        current_price = pos.get("current_price")
        entry_time = pos.get("entry_time")
        shares = pos.get("shares", 1)
        strategy_name = pos.get("strategy_name", "未標記策略")

        # 檢查是否應該出場
        exit_flag, reason = should_exit(entry_price, current_price, pos)

        if exit_flag:
            print(f"🔁 出場判定觸發：{symbol}｜理由：{reason}")
            execute_exit(
                symbol=symbol,
                entry_time=entry_time,
                exit_price=current_price,
                entry_price=entry_price,
                rsi=pos.get("rsi"),
                zscore=pos.get("zscore"),
                roc=pos.get("roc"),
                obv=pos.get("obv"),
                vwap=pos.get("vwap"),
                ema5=pos.get("ema5"),
                ema20=pos.get("ema20"),
                strategy_name=strategy_name,
                shares=shares,
                reason=reason  # ✅ 傳入出場理由
            )
            to_exit.append(symbol)

    return to_exit
