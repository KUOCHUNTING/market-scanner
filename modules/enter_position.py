from datetime import datetime

# 全域已建倉股票追蹤集（防重複建倉）
entered_positions = set()

# 假設以下變數已由其他模組定義（如 config.py）
# from config import capital_left, positions, compute_position_size
capital_left = 100000  # ✅ 假設初始資金（實際請用你自己的）
positions = {}

def compute_position_size(price):
    # ✅ 可自行改為更精細的風控計算
    shares = int(1000 // price)
    capital_used = shares * price
    return shares, capital_used

def enter_position(symbol, price, direction, signal_note,
                   rsi=None, zscore=None, strategy_name="未標記策略",
                   ema5=None, ema20=None, upper_band=None, lower_band=None, mid_band=None,
                   roc=None, obv=None, vwap=None, confidence_score=None,
                   strategy_display=None):
    global capital_left, positions

    # ✅ 價格合法性檢查
    if price is None or price <= 0:
        print(f"[錯誤] {symbol} 建倉失敗 ➜ 價格無效：{price}")
        return

    # ✅ 避免重複建倉
    if symbol in entered_positions:
        print(f"⛔ 已建倉過：{symbol}，略過")
        return

    # 加入已建倉名單
    entered_positions.add(symbol)

    # ✅ 計算股數與資金
    shares, capital_used = compute_position_size(price)

    # ✅ 防呆檢查
    if shares <= 0 or capital_used <= 0:
        print(f"[跳過] {symbol} 建倉失敗 ➜ 價格={price}｜股數={shares}｜資金=${capital_used:.2f}")
        return

    # ✅ 扣除資金
    capital_left -= capital_used
    print(f"[資金確認] 已扣資金：${capital_used:.2f}，剩餘資金：${capital_left:,.2f}")

    now = datetime.now()

    # ✅ 記錄部位資訊
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

    # ✅ 成功訊息
    print(f"[✅紀錄] 已建倉：{symbol} @ ${price:.2f}｜方向：{direction}｜股數：{shares}｜策略：{strategy_display or strategy_name}")
