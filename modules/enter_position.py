from datetime import datetime
from modules.connect_to_gsheet import write_entry_to_sheet
from modules.notify.discord_push import send_discord_message
from modules.notify.build_discord_message import build_entry_message
from modules.config import WEBHOOK_URL

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
                   obv=None, vwap=None, confidence_score=None,
                   strategy_display=None, match_score=None, ema_trend=None,
                   up_count=None, down_count=None,
                   close_price=None,
                   mean_hit_rate=None,
                   trend_hit_rate=None):
    global capital_left, positions

    if price is None or price <= 0:
        print(f"[錯誤] {symbol} 建倉失敗 ➜ 價格無效：{price}")
        return

    if symbol in entered_positions:
        print(f"⛔ 已建倉過：{symbol}，略過")
        return
    entered_positions.add(symbol)

    shares, capital_used = compute_position_size(price, direction)
    if shares <= 0 or capital_used <= 0:
        print(f"[跳過] {symbol} ➜ 建倉失敗：股數={shares}｜資金=${capital_used:.2f}")
        return

    capital_left -= capital_used
    print(f"[資金變化] {symbol} ➜ 花費 ${capital_used:.2f}｜剩餘資金 ${capital_left:,.2f}")

    now = datetime.now()

    # ✅ 紀錄部位
    positions[symbol] = {
        "direction": direction,
        "entry_price": price,
        "quantity": shares,
        "entry_time": now,
        "capital_used": capital_used,
        "sell_stage": 0,
        "max_gain": 0.0,
        "strategy": strategy_name,
        "strategy_display": strategy_display,
        "rsi": rsi,
        "zscore": zscore,
        "ema5": ema5,
        "ema20": ema20,
        "obv": obv,
        "vwap": vwap,
        "confidence_score": confidence_score,
        "close_price": close_price,
        "mean_hit_rate": mean_hit_rate,
        "trend_hit_rate": trend_hit_rate
    }

    # ✅ 寫入 Google Sheets
    try:
        print(f"[DEBUG] 嘗試寫入 Sheets ➜ {symbol}")
        write_entry_to_sheet(
            symbol=symbol,
            direction=direction,
            shares=shares,
            entry_capital=capital_used,
            strategy_name=strategy_display or strategy_name,
            confidence_score=confidence_score,
            capital_left=capital_left
        )
        print(f"✅【寫入成功】{symbol} ➜ 已寫入 Google Sheets 建倉紀錄")
    except Exception as e:
        print(f"❌【寫入失敗】{symbol} ➜ {e}")

    # ✅ 使用統一格式推播訊息
    if match_score is not None and up_count is not None and down_count is not None:
        message = build_entry_message(
            symbol=symbol,
            price=price,
            strategy_name=strategy_name,
            direction="多" if direction == "做多" else "空",
            confidence_score=confidence_score,
            rsi=rsi,
            zscore=zscore,
            ema5=ema5,
            ema20=ema20,
            bb_upper=bb_upper,
            bb_lower=bb_lower,
            obv=obv,
            strategy_type=strategy_display or "技術策略",
            trend_score=trend_hit_rate,
            rrov_score=match_score,
            mean_score=mean_hit_rate,
            signal_note=signal_note,
            shares=shares,
            capital_used=capital_used,
            capital_left=capital_left
        )
        send_discord_message(WEBHOOK_URL, message)

    print(f"[✅紀錄] 已建倉：{symbol} @ ${price:.2f}｜方向：{direction}｜股數：{shares}｜策略：{strategy_display or strategy_name}")
    print(f"✅【建倉成功】{symbol} ➜ 價格：${price:.2f}｜方向：{direction}｜股數：{shares}")

    return shares, capital_used, capital_left
