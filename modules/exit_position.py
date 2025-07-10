from datetime import datetime
from modules.calculate_exit_metrics import calculate_exit_metrics
from modules.notify.discord_push import send_discord_message
from modules.connect_to_gsheet import write_exit_to_sheet  # ← 根據你的寫入函數位置調整

def exit_position(symbol, current_price, position_data):
    exit_time = datetime.now()

    # 提取持倉資訊
    entry_price = position_data['entry_price']
    shares = position_data['shares']
    entry_time = position_data['entry_time']

    # 若 entry_time 是字串，轉為 datetime 物件
    if isinstance(entry_time, str):
        try:
            entry_time = datetime.fromisoformat(entry_time)
        except Exception:
            print(f"[錯誤] entry_time 無法轉換：{entry_time}")
            return

    # 防呆：價格或股數異常
    if entry_price is None or entry_price <= 0.05 or shares <= 0:
        print(f"[跳過] {symbol} ➜ 出場無效（entry_price={entry_price}, shares={shares}）")
        return

    # 計算績效
    return_rate, pnl, holding_minutes = calculate_exit_metrics(
        entry_price=entry_price,
        exit_price=current_price,
        shares=shares,
        entry_time=entry_time,
        exit_time=exit_time,
        direction=position_data['direction'],
        symbol=symbol
    )

    # 報酬率檢查
    if return_rate is None:
        print(f"[❌ 報酬率無效] {symbol} ➜ 可能被過濾或價格異常")
        return
    elif return_rate < -90 or return_rate > 500:
        print(f"[跳過] {symbol} ➜ 報酬率異常（{return_rate:.2f}%），可能是假價格")
        return

    # 寫入出場記錄
    write_exit_to_sheet(
        symbol=symbol,
        entry_time=entry_time,
        exit_time=exit_time,
        return_rate=return_rate,
        pnl=pnl,
        holding_minutes=holding_minutes,
        exit_price=current_price,
        rsi=position_data.get("rsi"),
        zscore=position_data.get("zscore"),
        roc=position_data.get("roc"),
        obv=position_data.get("obv"),
        vwap=position_data.get("vwap"),
        ema5=position_data.get("ema5"),
        ema20=position_data.get("ema20"),
        strategy_name=position_data.get("strategy_display", "未知策略")
    )

    # 出場提示
    print(f"[📤 出場完成] {symbol} ➜ 損益：${pnl:.2f}｜報酬率：{return_rate:.2f}%｜持倉：{holding_minutes:.1f} 分鐘")
