# test_enter_position.py
import pandas as pd
from datetime import datetime
import requests

# === 初始化變數 ===
positions = {}
capital_left = 100000
TOTAL_CAPITAL = 100000
POSITION_SIZE = 0.05

def compute_position_size(price):
    shares = int((TOTAL_CAPITAL * POSITION_SIZE) // price)
    capital_used = shares * price
    return shares, capital_used

# === 假設你有定義這個 Webhook（可以暫時留空）===
WEBHOOK_URL = ""  # 放你用來測試推播的 Webhook（可空）

# === 假設 Google Sheets 寫入函數 ===
def write_trade_to_sheet(**kwargs):
    print("📝 假裝寫入 Sheets：")
    for k, v in kwargs.items():
        print(f"{k}: {v}")
    print("✅ 測試寫入成功！")

def enter_position(symbol, price, direction, signal_note,
                   rsi=None, zscore=None, strategy_name="未標記策略",
                   ema5=None, ema20=None, upper_band=None, lower_band=None, mid_band=None,
                   roc=None, obv=None, vwap=None, confidence_score=None):
    global capital_left

    shares, capital_used = compute_position_size(price)
    if shares <= 0:
        print("❌ 股數為 0，建倉失敗")
        return

    capital_left -= capital_used
    now = datetime.now()

    positions[symbol] = {
        "direction": direction,
        "entry_price": price,
        "shares": shares,
        "capital_used": capital_used,
        "entry_time": now,
        "strategy": strategy_name
    }

    print(f"📌 成功建倉 {symbol}，投入資金 ${capital_used:.2f}，剩餘資金 ${capital_left:,.2f}")

    # 寫入 Sheets
    write_trade_to_sheet(
        strategy_type=strategy_name,
        symbol=symbol,
        direction=direction,
        entry_price=price,
        shares=shares,
        invested_capital=capital_used,
        rsi=rsi,
        zscore=zscore,
        roc=roc,
        obv=obv,
        vwap=vwap,
        confidence_score=confidence_score,
        signal_note=signal_note,
        sheet_webhook_url="https://docs.google.com/spreadsheets/d/14SSmjk2Ae3rqx0VyiVoVWBXpq0NVNvsLs1RWckuX4Ko/edit?gid=0#gid=0"  # 你自己的
    )

# === 測試建倉 ===
if __name__ == "__main__":
    enter_position(
        symbol="TSLA",
        price=195.55,
        direction="多",
        signal_note="測試進場 - RSI 超跌回升",
        rsi=32.5,
        zscore=-2.1,
        strategy_name="RROV",
        ema5=194.1,
        ema20=192.8,
        upper_band=200.0,
        lower_band=190.0,
        mid_band=195.0,
        roc=0.4,
        obv=1250000,
        vwap=194.9,
        confidence_score=0.91
    )

    print("\n📊 [測試完成後的持倉]")
    for s, p in positions.items():
        print(f"- {s}｜方向：{p['direction']}｜股數：{p['shares']}｜價格：{p['entry_price']}")
