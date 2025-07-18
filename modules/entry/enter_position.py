from modules.connect_to_gsheet import write_entry_to_sheet
from modules.notify.discord_push import send_discord_message
from modules.notify.build_discord_message import build_entry_message

def enter_position(
    symbol: str,
    price: float,
    direction: str,
    score: float,
    strategy_name: str,
    rsi=None,
    zscore=None,
    roc=None,
    obv=None,
    vwap=None,
    ema5=None,
    ema20=None,
    bb_upper=None,
    bb_lower=None,
    signal_note=None,
    trend_score=None,
    rrov_score=None,
    mean_score=None,
    take_profit_pct=0.08,
    stop_loss_pct=0.03,
    sheet_name: str = "進場紀錄"  # ✅ 支援傳入分頁名稱
):
    global capital_left, positions

    # 防止重複建倉
    if symbol in positions:
        return {"status": "skipped", "reason": "duplicate"}

    capital_used = 10000
    if capital_left < capital_used:
        return {"status": "skipped", "reason": "insufficient capital"}

    capital_left -= capital_used
    position = {
        "symbol": symbol,
        "price": price,
        "direction": direction,
        "score": score,
        "strategy": strategy_name,
        "rsi": rsi,
        "zscore": zscore,
        "roc": roc,
        "obv": obv,
        "vwap": vwap,
        "ema5": ema5,
        "ema20": ema20,
        "bb_upper": bb_upper,
        "bb_lower": bb_lower,
        "signal_note": signal_note,
        "trend_score": trend_score,
        "rrov_score": rrov_score,
        "mean_score": mean_score,
    }

    # ✅ 寫入 Google Sheets，支援分頁參數
    write_entry_to_sheet(position, sheet_name=sheet_name)

    # ✅ 推播 Discord
    message = build_entry_message(position)
    send_discord_message(message)

    # 加入持倉紀錄
    positions[symbol] = position
    return {"status": "entered", "position": position}
