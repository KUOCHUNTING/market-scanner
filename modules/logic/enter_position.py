from datetime import datetime
from modules.config import capital_left, WEBHOOK_URL
from modules.utils.connect_to_gsheet import write_entry_to_sheet
from modules.notify.discord_push import send_discord_message
from modules.notify.build_discord_message import build_entry_message

# === 全域變數（主控設定的資金與持倉）
entered_positions = set()
positions = {}

# ✅ 建倉數量與資金使用計算
def compute_position_size(price, max_capital_per_trade=1000):
    shares = int(max_capital_per_trade // price)
    capital_used = round(shares * price, 2)
    return shares, capital_used

# ✅ 建倉執行函數
def enter_position(symbol, price, direction, signal_note,
                   strategy_name="未標記策略", score=None, confidence_score=None,
                   rsi=None, zscore=None, ema5=None, ema20=None,
                   bb_upper=None, bb_lower=None, obv=None,
                   trend_score=None, rrov_score=None, mean_score=None):

    global capital_left, entered_positions, positions

    if symbol in entered_positions:
        print(f"⚠️ 已建倉過 ➜ 略過 {symbol}")
        return

    # 計算建倉股數與資金
    shares, capital_used = compute_position_size(price)
    if shares <= 0 or capital_used > capital_left:
        print(f"⚠️ 資金不足 ➜ 略過 {symbol}｜需要 ${capital_used:.2f}，剩餘 ${capital_left:.2f}")
        return

    capital_left -= capital_used
    entry_time = datetime.now()

    # 更新持倉記錄
    positions[symbol] = {
        "entry_price": price,
        "entry_time": entry_time,
        "quantity": shares,
        "capital_used": capital_used,
        "direction": direction,
        "strategy": strategy_name,
        "confidence_score": confidence_score,
        "signal_note": signal_note,
        "sell_stage": 0,
        "max_gain": 0.0
    }
    entered_positions.add(symbol)

    # 建立推播訊息
    message = build_entry_message(
        symbol=symbol,
        price=price,
        strategy_type=strategy_name,
        signal_type=strategy_name,  # 可依策略再細分類型
        strategy_name=strategy_name,
        signal_note=signal_note,
        direction=direction,
        score=score,
        confidence_score=confidence_score,
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
        shares=shares,
        capital_used=capital_used,
        capital_left=capital_left
    )

    # 推播到 Discord
    send_discord_message(WEBHOOK_URL, message)

    # 寫入 Google Sheets
    write_entry_to_sheet(
        symbol=symbol,
        entry_time=entry_time,
        entry_price=price,
        direction=direction,
        quantity=shares,
        strategy_name=strategy_name,
        confidence_score=confidence_score,
        capital_left=capital_left
    )

    print(f"✅【建倉成功】{symbol} ➜ {shares} 股｜${capital_used:.2f}｜剩餘資金：${capital_left:.2f}")
