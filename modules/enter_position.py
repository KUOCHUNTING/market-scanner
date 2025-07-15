from datetime import datetime
from modules.connect_to_gsheet import write_entry_to_sheet
from modules.notify.discord_push import send_discord_message
from modules.notify.build_discord_message import build_entry_message
from modules.config import WEBHOOK_URL

# === 📦 全域變數（資金與持倉）===
entered_positions = set()
capital_left = 100000  # 可改 config 載入
positions = {}

def compute_position_size(price, direction="做多"):
    max_capital = 1000
    shares = int(max_capital // price)
    capital_used = shares * price

    # 做空可考慮放大保證金需求（如：1.2 倍）
    if direction == "做空":
        capital_used *= 1.2

    return shares, capital_used

def enter_position(symbol, price, direction, signal_note,
                   rsi=None, zscore=None, strategy_name="未標記策略",
                   ema5=None, ema20=None, bb_upper=None, bb_lower=None,
                   obv=None, trend_score=None, rrov_score=None, mean_score=None,
                   score=None, confidence_score=None):

    global capital_left

    shares, capital_used = compute_position_size(price, direction)
    if capital_used > capital_left:
        print(f"💸 資金不足 ➜ {symbol} 需要 {capital_used:.2f}，剩餘 {capital_left:.2f}")
        return

    capital_left -= capital_used
    positions[symbol] = {
        "價格": price,
        "方向": direction,
        "股數": shares,
        "投入資金": capital_used,
        "策略": strategy_name
    }

    if not WEBHOOK_URL.startswith("https://discord.com/api/webhooks/"):
        print(f"❌ 錯誤：WEBHOOK_URL 被覆蓋為 ➜ {WEBHOOK_URL}")
        raise ValueError("WEBHOOK_URL 格式錯誤，請檢查是否被錯誤覆蓋")
    
    message = build_entry_message(
        symbol=symbol,
        price=price,
        strategy_type="技術策略",
        signal_type="技術策略",
        strategy_name=strategy_name,
        signal_note=signal_note,
        direction=direction,
        score=score,
        confidence_score=confidence_score,
        rsi=rsi, zscore=zscore,
        ema5=ema5, ema20=ema20,
        bb_upper=bb_upper, bb_lower=bb_lower,
        obv=obv,
        trend_score=trend_score,
        rrov_score=rrov_score,
        mean_score=mean_score,
        shares=shares,
        capital_used=capital_used,
        capital_left=capital_left
    )

    send_discord_message(message, WEBHOOK_URL)
    write_entry_to_sheet(symbol, direction, shares, capital_used, strategy_name, confidence_score, capital_left)
