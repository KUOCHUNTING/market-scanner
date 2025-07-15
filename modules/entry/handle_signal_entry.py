from modules.entry.handle_entry import enter_position
from modules.utils.format import get_last_value
from modules.notify.build_discord_message import build_entry_message
from modules.notify.discord_push import send_discord_message
from modules.config import WEBHOOK_URL

def handle_signal_entry(symbol, latest_price, direction, score, strategy_name,
                        signal_type, signal_note, indicators,
                        trend_score=None, rrov_score=None, mean_score=None,
                        capital_left=None):
    """
    技術策略建倉流程
    """
    result = enter_position(symbol, latest_price, direction, score, strategy_name)
    if result is None:
        return None

    shares, capital_used = result[:2]

    message = build_entry_message(
        symbol=symbol,
        price=latest_price,
        strategy_type="📌 技術選股",
        signal_type=signal_type,
        strategy_name=strategy_name,
        signal_note=signal_note,
        direction=direction,
        score=score,
        confidence_score=score,
        rsi=get_last_value(indicators.get("rsi")),
        zscore=get_last_value(indicators.get("zscore")),
        ema5=get_last_value(indicators.get("ema_5")),
        ema20=get_last_value(indicators.get("ema_20")),
        bb_upper=get_last_value(indicators.get("bb_upper")),
        bb_lower=get_last_value(indicators.get("bb_lower")),
        obv=get_last_value(indicators.get("obv")),
        trend_score=trend_score,
        rrov_score=rrov_score,
        mean_score=mean_score,
        shares=shares,
        capital_used=capital_used,
        capital_left=capital_left
    )
    send_discord_message(WEBHOOK_URL, message)
    return shares, capital_used
