from datetime import datetime
from modules.connect_to_gsheet import write_entry_to_sheet
from modules.notify.discord_push import send_discord_message
from modules.config import WEBHOOK_URL

# === 📦 全域變數（資金與持倉）===
entered_positions = set()
capital_left = 100000  # 可改由 config 載入
positions = {}

# ✅ 計算建倉股數與資金
def compute_position_size(price, direction="做多"):
    max_capital = 1000 if direction == "做多" else 1000  # 空單可視需求調整金額
    shares = int(max_capital // price)
    capital_used = shares * price
    return shares, capital_used

# ✅ 主建倉函數
def enter_position(symbol, price, direction, signal_note,
                   rsi=None, zscore=None, strategy_name="未標記策略",
                   ema5=None, ema20=None, upper_band=None, lower_band=None, mid_band=None,
                   roc=None, obv=None, vwap=None, confidence_score=None,
                   strategy_display=None, match_score=None, ema_trend=None,
                   up_count=None, down_count=None,
                   close_price=None,
                   mean_hit_rate=None,
                   trend_hit_rate=None
                   ):
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
        "roc": roc,
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

    # ✅ 成功推播（策略訊號）
    if match_score is not None and up_count is not None and down_count is not None:
        direction_emoji = "📈" if direction == "做多" else "📉"
        trend_emoji = "🟢" if ema_trend == "多" else "🔴" if ema_trend == "空" else "⚪"
        trend_text = ema_trend or "未知"
        win_rate = match_score * 100

        message  = f"{direction_emoji}【技術策略 訊號】{symbol}\n\n"
        message += f"📊 類型：策略（方向：{direction}）\n"
        message += f"💵 收盤價：${close_price:.2f}\n"
        message += f"🧠 信心分數：{confidence_score:.2f}\n"
        message += f"🎯 RROV 命中率：{win_rate:.2f}%｜均值：{(mean_hit_rate or 0)*100:.2f}%｜順勢：{(trend_hit_rate or 0)*100:.2f}%\n\n"
        message += f"📈 技術傾向：{trend_emoji} 技術偏{trend_text}\n"
        message += f"📉 EMA 趨勢：上漲 {up_count} 次｜下跌 {down_count} 次（偏{ema_trend}）\n\n"
        message += f"📋 訊號說明：\n{signal_note}\n\n"
        message += f"🧠 策略：{strategy_display or strategy_name}\n\n"
        message += f"📦 股數：{shares} 股\n"
        message += f"💰 進場資金：${int(capital_used):,}\n"
        message += f"💼 剩餘資金：${int(capital_left):,}"

        send_discord_message(WEBHOOK_URL, message)

    print(f"[✅紀錄] 已建倉：{symbol} @ ${price:.2f}｜方向：{direction}｜股數：{shares}｜策略：{strategy_display or strategy_name}")
    print(f"✅【建倉成功】{symbol} ➜ 價格：${price:.2f}｜方向：{direction}｜股數：{shares}")

    return shares, capital_used, capital_left
