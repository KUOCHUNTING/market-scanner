import os
from datetime import datetime
from modules.notify.discord_push import send_discord_message
from modules.notify.build_discord_message import build_entry_message_from_position  # ✅ 改這行
from modules.utils.gsheet_writer import write_entry_to_sheet, write_exit_to_sheet
from dotenv import load_dotenv

# ✅ 讀取環境變數
load_dotenv()
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# ✅ 全域資金與持倉管理
capital_left = float(os.getenv("CAPITAL_LEFT", "100000"))  # 可調整初始資金
positions = {}  # symbol -> position dict

# ✅ 主建倉函數
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
    signal_type=None,
    strategy_type=None,
    take_profit_pct=0.08,
    stop_loss_pct=0.03,
    sheet=None,                  # ✅ 新增
    sheet_name=None              # ✅ 新增
):
    global capital_left, positions

    # ✅ 重複建倉檢查
    if symbol in positions:
        print(f"[略過] {symbol} 已持有倉位")
        return None

    # ✅ 檢查剩餘資金
    if capital_left < 3000:
        print(f"[略過] 資金不足 ➜ 剩餘 ${capital_left:.2f}")
        return None

    # ✅ 假設全倉進場
    quantity = int(capital_left // price)
    if quantity == 0:
        print(f"[略過] 單價過高，無法進場 ➜ {symbol} at ${price}")
        return None

    capital_used = quantity * price
    entry_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    position = {
        "symbol": symbol,
        "entry_time": entry_time,
        "entry_price": price,
        "direction": direction,
        "shares": quantity,
        "capital_used": capital_used,
        "strategy_name": strategy_name,
        "strategy_type": strategy_type,   # ✅ 新增
        "signal_type": signal_type,       # ✅ 新增
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

    # ✅ 更新全域倉位與資金
    positions[symbol] = position
    capital_left -= capital_used

    # ✅ 推播 Discord 訊息
    message = build_entry_message_from_position(position)  # ✅ 正確用法
    send_discord_message(DISCORD_WEBHOOK_URL, message)

    # ✅ 寫入 Google Sheets
    if sheet:
        write_entry_to_sheet(position, sheet)

    print(f"✅ 建倉成功：{symbol}｜方向：{direction}｜股數：{quantity}｜價格：${price:.2f}｜策略：{strategy_name}")
    return position, message, capital_left
