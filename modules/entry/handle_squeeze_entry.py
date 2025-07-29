import os
from dotenv import load_dotenv
from modules.notify.build_discord_message import build_breakout_message
from modules.notify.discord_push import send_discord_message

load_dotenv()
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

def handle_squeeze_entry(symbol, squeeze_result, sheet=None, position_manager=None):
    """
    擠壓突破策略建倉流程：
    - 推播：格式化訊息推送至 Discord
    - 建倉：透過 position_manager.add_position()
    """
    if not squeeze_result or not position_manager:
        return None

    print(f"📣 [{symbol}] 擠壓突破策略觸發！")

    # ✅ 組裝推播訊息
    msg = build_breakout_message(
        symbol=symbol,
        price=squeeze_result.get("close"),
        direction=squeeze_result.get("direction"),
        strategy_name=squeeze_result.get("strategy_name"),
        score=squeeze_result.get("score"),
        rsi=squeeze_result.get("rsi"),
        zscore=squeeze_result.get("zscore"),
        roc=squeeze_result.get("roc"),
        obv=squeeze_result.get("obv"),
        vwap=squeeze_result.get("vwap"),
        ema5=squeeze_result.get("ema5"),
        ema20=squeeze_result.get("ema20"),
        bb_upper=squeeze_result.get("bb_upper"),
        bb_lower=squeeze_result.get("bb_lower"),
        confidence_score=squeeze_result.get("confidence_score"),
        shares=None,
        capital_used=None,
        capital_left=position_manager.capital_left
    )
    send_discord_message(msg, webhook_url=WEBHOOK_URL)

    # ✅ 透過 PositionManager 建倉
    result = position_manager.add_position(
        symbol=symbol,
        price=squeeze_result.get("close"),
        direction=squeeze_result.get("direction"),
        score=squeeze_result.get("score"),
        confidence_score=squeeze_result.get("confidence_score"),
        strategy_name=squeeze_result.get("strategy_name"),
        strategy_type="squeeze",
        signal_type="breakout",
        signal_note="擠壓突破",
        rsi=squeeze_result.get("rsi"),
        zscore=squeeze_result.get("zscore"),
        roc=squeeze_result.get("roc"),
        obv=squeeze_result.get("obv"),
        vwap=squeeze_result.get("vwap"),
        ema5=squeeze_result.get("ema5"),
        ema20=squeeze_result.get("ema20"),
        bb_upper=squeeze_result.get("bb_upper"),
        bb_lower=squeeze_result.get("bb_lower"),
        sheet=sheet
    )

    return result
