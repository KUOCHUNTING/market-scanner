from datetime import datetime
from modules.connect_to_gsheet import write_entry_to_sheet  # ✅ 寫入 Sheets

# === 📦 全域變數（資金與持倉）===
entered_positions = set()
capital_left = 100000  # ✅ 可改由 config 載入
positions = {}

# ✅ 計算建倉股數與資金
def compute_position_size(price):
    shares = int(1000 // price)  # 例：每檔最多花 $1000，可調整
    capital_used = shares * price
    return shares, capital_used

# ✅ 主建倉函數
def enter_position(symbol, price, direction, signal_note,
                   rsi=None, zscore=None, strategy_name="未標記策略",
                   ema5=None, ema20=None, upper_band=None, lower_band=None, mid_band=None,
                   roc=None, obv=None, vwap=None, confidence_score=None,
                   strategy_display=None):
    global capital_left, positions

    # 防呆：價格不合法
    if price is None or price <= 0:
        print(f"[錯誤] {symbol} 建倉失敗 ➜ 價格無效：{price}")
        return

    # 防重複建倉
    if symbol in entered_positions:
        print(f"⛔ 已建倉過：{symbol}，略過")
        return
    entered_positions.add(symbol)

    # 計算建倉數量與成本
    shares, capital_used = compute_position_size(price)
    if shares <= 0 or capital_used <= 0:
        print(f"[跳過] {symbol} ➜ 建倉失敗：股數={shares}｜資金=${capital_used:.2f}")
        return

    # 扣除資金
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
    }

    # ✅ 寫入 Google Sheets
    try:
        print(f"[DEBUG] 嘗試寫入 Sheets ➜ {symbol}")  # ←
        write_entry_to_sheet(
            symbol=symbol,
            direction=direction,
            shares=shares,
            entry_capital=capital_used,
            strategy_name=strategy_display or strategy_name,
            confidence_score=confidence_score,
            capital_left=capital_left
        )
    except Exception as e:
        print(f"[錯誤] 無法寫入 Google Sheets 建倉紀錄：{e}")

    # ✅ 成功推播 / 日誌
    print(f"[✅紀錄] 已建倉：{symbol} @ ${price:.2f}｜方向：{direction}｜股數：{shares}｜策略：{strategy_display or strategy_name}")

    print(f"✅【建倉成功】{symbol} ➜ 價格：${latest_price:.2f}｜方向：{direction}｜股數：{shares}")

    return shares, capital_used, capital_left
