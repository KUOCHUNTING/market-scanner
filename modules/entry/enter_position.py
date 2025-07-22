import os
from datetime import datetime
from dotenv import load_dotenv
from modules.notify.discord_push import send_discord_message
from modules.notify.build_discord_message import build_entry_message_from_position
from modules.utils.gsheet_writer import write_entry_to_sheet

# ✅ 強制從專案根目錄載入 .env
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", ".env")
load_dotenv(dotenv_path)

# ✅ 載入 Webhook 與初始資金（支援外部覆蓋）
DEFAULT_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
capital_left = float(os.getenv("CAPITAL_LEFT", "100000"))  # ✅ 初始資金
positions = {}  # symbol -> position dict

print(f"[資金初始化] capital_left = ${capital_left:.2f}")

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
    trend_dir=None,
    rrov_dir=None,
    mean_dir=None,
    signal_type=None,
    strategy_type=None,
    take_profit_pct=0.08,
    stop_loss_pct=0.03,
    sheet=None,
    sheet_name=None,
    sector=None,
    webhook_url=None  # ✅ 可選：傳入外部 webhook
):
    global capital_left, positions

    # ✅ 重複建倉檢查
    if symbol in positions:
        msg = f"[略過] {symbol} 已持有倉位"
        print(msg)
        return None, msg, capital_left

    # ✅ 資金不足檢查
    if capital_left < 3000:
        msg = f"[略過] 資金不足 ➜ 剩餘 ${capital_left:.2f}"
        print(msg)
        return None, msg, capital_left

    # ✅ 假設全倉進場
    quantity = int(capital_left // price)
    if quantity == 0:
        msg = f"[略過] 單價過高，無法進場 ➜ {symbol} at ${price:.2f}"
        print(msg)
        return None, msg, capital_left

    # ✅ 建倉金額
    capital_used = quantity * price
    entry_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ✅ 建立持倉物件
    position = {
        "symbol": symbol,
        "entry_time": entry_time,
        "entry_price": price,
        "price": price,
        "direction": direction,
        "shares": quantity,
        "capital_used": capital_used,
        "strategy_name": strategy_name,
        "strategy_type": strategy_type,
        "signal_type": signal_type,
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
        "trend_dir": trend_dir,
        "rrov_score": rrov_score,
        "rrov_dir": rrov_dir,
        "mean_score": mean_score,
        "mean_dir": mean_dir,
        "signal_note": signal_note
    }

    # ✅ 更新持倉與資金
    positions[symbol] = position
    capital_left -= capital_used

    # ✅ 組裝訊息
    message = build_entry_message_from_position(position)

    # ✅ 推播 Discord（可傳入 webhook_url）
    webhook = webhook_url or DEFAULT_WEBHOOK_URL
    if webhook and "discord.com" in webhook:
        send_discord_message(webhook, message)
    else:
        print("[⚠️ 略過推播] 未提供有效的 Discord Webhook URL")

    # ✅ 寫入 Google Sheets
    if sheet:
        write_entry_to_sheet(entry=position, sheet=sheet, shares=quantity)

    print(f"✅ 建倉成功：{symbol}｜方向：{direction}｜股數：{quantity}｜價格：${price:.2f}｜策略：{strategy_name}")
    return position, message, capital_left
