import os
from datetime import datetime
from modules.connect_to_gsheet import write_entry_to_sheet
from modules.notify.discord_push import send_discord_message
from modules.notify.build_discord_message import build_entry_message
from dotenv import load_dotenv
from modules.config.settings import DISCORD_WEBHOOK_URL

load_dotenv()

# ✅ 全域資金與持倉管理
capital_left = float(os.getenv("CAPITAL_LEFT", "100000"))
positions = {}  # symbol -> position dict

# ✅ 主建倉函數（加入 sheet 參數）
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
    sheet=None  # ✅ 加入共用 Google Sheet 分頁物件
):
    global capital_left, positions

    if symbol in positions:
        print(f"⚠️ 已持有 {symbol}，跳過建倉")
        return None, 0, 0

    allocation = 0.1
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
    entry_time = datetime.now()

    position = {
        "symbol": symbol,
        "entry_time": entry_time,
        "entry_price": price,
        "direction": direction,
        "shares": quantity,
        "capital_used": capital_used,
        "strategy_name": strategy_name,
        "confidence_score": score,
        "take_profit_pct": take_profit_pct,
        "stop_loss_pct": stop_loss_pct,
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
        "mean_score": mean_score,
        "signal_note": signal_note
    }

    positions[symbol] = position

    # ✅ 共用 sheet 寫入（改為傳入）
    if sheet is not None:
        write_entry_to_sheet(position, sheet=sheet)
    else:
        print("⚠️ 未傳入 Google Sheet 工作表，跳過寫入")

    # ✅ Discord 推播
    msg = build_entry_message(
        symbol=symbol,
        price=price,
        strategy_type="技術選股",
        signal_type=strategy_name,
        strategy_name=strategy_name,
        signal_note=signal_note,
        direction=direction,
        score=score,
        confidence_score=score,
        rsi=rsi,
        zscore=zscore,
        ema5=ema5,
        ema20=ema20,
        bb_upper=bb_upper,
        bb_lower=bb_lower,
        obv=obv,
        trend_score=trend_score,
        rrov_score=rrov_score,
        mean_score=mean_score,
        shares=quantity,
        capital_used=capital_used,
        capital_left=capital_left
    )
    send_discord_message(msg, DISCORD_WEBHOOK_URL)

    print(f"✅ 建倉完成：{symbol} × {quantity} 股，資金 ${capital_used:.2f}｜剩餘資金 ${capital_left:.2f}")
    return symbol, capital_used, quantity
