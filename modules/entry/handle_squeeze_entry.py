from modules.notify.build_discord_message import build_breakout_message
from modules.notify.discord_push import send_discord_message
from modules.entry.enter_position import enter_position
from modules.config.config import WEBHOOK_URL

def handle_squeeze_entry(symbol, squeeze_result, sheet):
    """
    擠壓突破策略建倉流程：
    - 觸發條件：進入擠壓區後突破且符合技術指標
    - 推播：格式化訊息推送至 Discord
    - 建倉：調用 enter_position() 並寫入 Google Sheets
    """
    if not squeeze_result:
        return None

    print(f"📣 [Squeeze] {symbol} 擠壓突破策略觸發！")

    # ✅ 組裝推播訊息（先推技術訊號摘要）
    msg = build_breakout_message(
        symbol=symbol,
        price=squeeze_result.get("close"),
        direction=squeeze_result.get("direction"),
        strategy_name=squeeze_result.get("strategy_name"),
        score=squeeze_result.get("score"),
        rsi=squeeze_result.get("rsi"),
        zscore=squeeze_result.get("zscore"),
        ema5=squeeze_result.get("ema5"),
        ema20=squeeze_result.get("ema20"),
        bb_upper=squeeze_result.get("bb_upper"),
        bb_lower=squeeze_result.get("bb_lower"),
        obv=squeeze_result.get("obv")
    )
    send_discord_message(WEBHOOK_URL, msg)

    # ✅ 實際建倉
    result = enter_position(
        symbol=symbol,
        price=squeeze_result.get("close"),
        direction=squeeze_result.get("direction"),
        strategy_name=squeeze_result.get("strategy_name"),
        score=squeeze_result.get("score"),
        signal_note="突破布林通道與壓縮區間",
        signal_type="擠壓突破",
        strategy_type="Squeeze 策略",
        rsi=squeeze_result.get("rsi"),
        zscore=squeeze_result.get("zscore"),
        ema5=squeeze_result.get("ema5"),
        ema20=squeeze_result.get("ema20"),
        bb_upper=squeeze_result.get("bb_upper"),
        bb_lower=squeeze_result.get("bb_lower"),
        obv=squeeze_result.get("obv"),
        sheet=sheet_entry
    )

    if result:
        position, message, capital_left = result
        return position, message, capital_left
    else:
        return None
