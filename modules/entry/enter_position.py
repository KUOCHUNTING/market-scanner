import os
from datetime import datetime
from modules.connect_to_gsheet import write_entry_to_sheet
from modules.notify.discord_push import send_discord_message
from modules.notify.build_discord_message import build_entry_message

# ✅ 資金控管（環境變數或 config 中）
capital_left = float(os.getenv("CAPITAL_LEFT", "100000"))

# ✅ 建倉主函式
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
    mean_score=None
):
    global capital_left

    # ✅ 建倉資金比例與股數
    allocation = 0.1  # 每筆使用 10%
    capital_used = capital_left * allocation
    if capital_used < price:
        print(f"⚠️ 資金不足，無法建倉 {symbol}")
        return None, 0, 0

    quantity = int(capital_used // price)
    if quantity == 0:
        print(f"⚠️ 價格過高，無法購買任何股數：{symbol}")
        return None, 0, 0

    capital_used = quantity * price
    capital_left -= capital_used

    # ✅ 整理建倉紀錄
    entry = {
        "entry_time": datetime.now(),
        "symbol": symbol,
        "price": price,
        "shares": quantity,
        "capital_used": capital_used,
        "direction": direction,
        "strategy_name": strategy_name,
        "confidence_score": score,
        "signal_note": signal_note,
        "rsi": rsi,
        "zscore": zscore,
        "roc": roc,
        "obv": obv,
        "vwap": vwap,
        "ema5": ema5,
        "ema20": ema20,
        "bb_upper": bb_upper,
        "bb_lower": bb_lower,
        "trend_score": trend_score,
        "rrov_score": rrov_score,
        "mean_score": mean_score
    }

    # ✅ 寫入 Google Sheets
    write_entry_to_sheet(entry)

    # ✅ 推播 Discord
    msg = build_entry_message(entry)
    send_discord_message(msg)

    return symbol, capital_used, quantity
