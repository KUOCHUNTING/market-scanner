# 模組位置：modules/entry/handle_entry.py
from modules.utils.connect_to_gsheet import connect_to_gsheet
from modules.utils.gsheet_writer import write_entry_to_sheet
from datetime import datetime
from modules.notify.discord_push import send_discord_message
from modules.notify.build_discord_message import (
    build_entry_message,
    build_mean_reversion_message,
    build_rrov_message,
    build_trend_message,
    build_breakout_message
)
from modules.config.config import WEBHOOK_URL  

# === 📦 全域變數（資金與持倉）===
entered_positions = set()
capital_left = 100000  # 可改由 config 載入
positions = {}

# ✅ 計算建倉股數與資金
def compute_position_size(price, direction="做多"):
    max_capital = 1000  # 可依方向設定不同上限
    shares = int(max_capital // price)
    capital_used = shares * price
    return shares, capital_used

# ✅ 主建倉函數
def enter_position(symbol, price, direction, signal_note,
                   rsi=None, zscore=None, strategy_name="未標記策略",
                   ema5=None, ema20=None, bb_upper=None, bb_lower=None,
                   obv=None, vwap=None,
                   strategy_type=None, signal_type=None, score=None, confidence_score=None,
                   trend_score=None, rrov_score=None, mean_score=None):
    global capital_left, entered_positions, positions

    # ⛔ 防呆：避免重複建倉
    if symbol in entered_positions:
        print(f"⚠️ 已建倉過：{symbol}，跳過")
        return

    # ✅ 計算持股數與資金
    shares, capital_used = compute_position_size(price, direction)

    if capital_used > capital_left:
        print(f"❌ 資金不足：可用 {capital_left:.2f}，需要 {capital_used:.2f}")
        return

    # ✅ 建倉紀錄
    entry_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    capital_left -= capital_used
    entered_positions.add(symbol)
    positions[symbol] = {
        "symbol": symbol,
        "entry_time": entry_time,
        "entry_price": price,
        "shares": shares,
        "direction": direction,
        "capital_used": capital_used,
        "strategy_name": strategy_name
    }

    # ✅ 推播訊息格式
    if strategy_type == "squeeze_breakout":
        msg = build_breakout_message(
            symbol=symbol,
            price=price,
            strategy_name=strategy_name,
            signal_note=signal_note,
            direction=direction,
            score=score,
            confidence_score=confidence_score,
            rsi=rsi, zscore=zscore, ema5=ema5, ema20=ema20,
            bb_upper=bb_upper, bb_lower=bb_lower, obv=obv,
            shares=shares, capital_used=capital_used, capital_left=capital_left
        )
    elif strategy_type == "mean":
        msg = build_mean_reversion_message(
            symbol=symbol, price=price,
            direction=direction,
            strategy_name=strategy_name,
            signal_note=signal_note,
            score=score, confidence_score=confidence_score,
            rsi=rsi, zscore=zscore, ema5=ema5, ema20=ema20,
            shares=shares, capital_used=capital_used, capital_left=capital_left
        )
    elif strategy_type == "trend":
        msg = build_trend_message(
            symbol=symbol, price=price,
            direction=direction,
            strategy_name=strategy_name,
            signal_note=signal_note,
            score=score, confidence_score=confidence_score,
            trend_score=trend_score,
            ema5=ema5, ema20=ema20, rsi=rsi, obv=obv,
            shares=shares, capital_used=capital_used, capital_left=capital_left
        )
    elif strategy_type == "rrov":
        msg = build_rrov_message(
            symbol=symbol, price=price,
            direction=direction,
            strategy_name=strategy_name,
            signal_note=signal_note,
            score=score, confidence_score=confidence_score,
            rrov_score=rrov_score,
            ema5=ema5, bb_upper=bb_upper, obv=obv,
            shares=shares, capital_used=capital_used, capital_left=capital_left
        )
    else:
        msg = build_entry_message(
            symbol=symbol, price=price,
            strategy_type=strategy_type,
            signal_type=signal_type,
            strategy_name=strategy_name,
            signal_note=signal_note,
            direction=direction,
            score=score, confidence_score=confidence_score,
            rsi=rsi, zscore=zscore, ema5=ema5, ema20=ema20,
            bb_upper=bb_upper, bb_lower=bb_lower, obv=obv,
            trend_score=trend_score, rrov_score=rrov_score, mean_score=mean_score,
            shares=shares, capital_used=capital_used, capital_left=capital_left
        )

    # ✅ 推送至 Discord
    send_discord_message(WEBHOOK_URL, msg)

    # ✅ 寫入 Google Sheets
    write_entry_to_sheet({
        "symbol": symbol,
        "entry_time": entry_time,
        "price": price,
        "direction": direction,
        "strategy_name": strategy_name,
        "signal_note": signal_note,
        "shares": shares,
        "capital_used": capital_used,
        "rsi": rsi,
        "zscore": zscore,
        "obv": obv,
        "vwap": vwap,
        "ema5": ema5,
        "ema20": ema20,
        "bb_upper": bb_upper,
        "bb_lower": bb_lower,
        "trend_score": trend_score,
        "rrov_score": rrov_score,
        "mean_score": mean_score,
        "confidence_score": confidence_score
    })

    return symbol, capital_used, shares
