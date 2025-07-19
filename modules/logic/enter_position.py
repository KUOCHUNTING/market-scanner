from datetime import datetime
from modules.config import capital_left, WEBHOOK_URL, GSHEET_URL, GSHEET_KEY_BASE64
from modules.utils.connect_to_gsheet import connect_to_gsheet, write_entry_to_sheet
from modules.notify.discord_push import send_discord_message
from modules.notify.build_discord_message import build_entry_message

# === 全域變數
entered_positions = set()
positions = {}

# ✅ 建倉數量與資金使用計算
def compute_position_size(price, max_capital_per_trade=1000):
    shares = int(max_capital_per_trade // price)
    capital_used = round(shares * price, 2)
    return shares, capital_used

# ✅ 主建倉函數
ef enter_position(
    symbol, price, direction, signal_note,
    strategy_name="未標記策略", score=None, confidence_score=None,
    rsi=None, zscore=None, ema5=None, ema20=None,
    bb_upper=None, bb_lower=None, obv=None,
    trend_score=None, rrov_score=None, mean_score=None,
    signal_type="技術信號", strategy_type="技術策略",
    sheet=None
):
    global capital_left, entered_positions, positions

    if symbol in entered_positions:
        print(f"⚠️ 已建倉過 ➜ 略過 {symbol}")
        return None, None, None  # ✅ 統一格式

    shares, capital_used = compute_position_size(price)
    if shares <= 0 or capital_used > capital_left:
        print(f"⚠️ 資金不足 ➜ 略過 {symbol}｜需要 ${capital_used:.2f}，剩餘 ${capital_left:.2f}")
        return None, None, None  # ✅ 統一格式

    capital_left -= capital_used
    entry_time = datetime.now()

    # ✅ 更新持倉記錄
    positions[symbol] = {
        "entry_price": price,
        "entry_time": entry_time,
        "shares": shares,                     # ✅ 改為 shares
        "capital_used": capital_used,
        "direction": direction,
        "strategy_name": strategy_name,       # ✅ 重點：欄位名稱必須正確
        "confidence_score": confidence_score,
        "signal_note": signal_note,
        "sell_stage": 0,
        "max_gain": 0.0
    }
    entered_positions.add(symbol)

    # ✅ Discord 推播訊息
    message = build_entry_message(
        symbol=position["symbol"],
        price=position["price"],
        strategy_type=position.get("strategy_type", "技術策略"),
        signal_type=position.get("signal_type", "技術信號"),
        strategy_name=position["strategy_name"],
        signal_note=position["signal_note"],
        direction=position["direction"],
        score=position.get("score"),
        confidence_score=position.get("confidence_score"),
        rsi=position.get("rsi"),
        zscore=position.get("zscore"),
        ema5=position.get("ema5"),
        ema20=position.get("ema20"),
        bb_upper=position.get("bb_upper"),
        bb_lower=position.get("bb_lower"),
        obv=position.get("obv"),
        trend_score=position.get("trend_score"),
        rrov_score=position.get("rrov_score"),
        mean_score=position.get("mean_score"),
        shares=position.get("shares"),
        capital_used=position.get("capital_used"),
        capital_left=position.get("capital_left"),
    )
    from modules.config import WEBHOOK_URL  # ✅ 確保有引入 webhook 設定
    send_discord_message(message, WEBHOOK_URL)

    # ✅ Sheets 寫入（直接用完整 dict）
    write_entry_to_sheet(positions[symbol])

    print(f"✅【建倉成功】{symbol} ➜ {shares} 股｜${capital_used:.2f}｜剩餘資金：${capital_left:.2f}")
    return shares, capital_used, shares  # 或者其他你希望的第三個欄位
