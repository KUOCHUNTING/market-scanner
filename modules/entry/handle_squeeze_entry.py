from modules.notify.build_discord_message import build_breakout_message
from modules.notify.discord_push import send_discord_message
from modules.entry.enter_position import enter_position  # ✅ 用新版的
from modules.config.config import WEBHOOK_URL

def handle_squeeze_entry(symbol, squeeze_result):
    """
    擠壓突破策略建倉流程
    """
    if not squeeze_result:
        return None

    print(f"📣 [{symbol}] 擠壓突破策略觸發！")
    msg = build_breakout_message(squeeze_result)
    send_discord_message(WEBHOOK_URL, msg)

    shares, capital_used, _ = enter_position(
        symbol=symbol,
        price=squeeze_result["close"],
        direction=squeeze_result["direction"],
        score=squeeze_result["score"],
        strategy_name=squeeze_result["strategy_name"],
        rsi=squeeze_result.get("rsi"),
        ema5=squeeze_result.get("ema_5"),
        ema20=squeeze_result.get("ema_20"),
        signal_note="Squeeze OFF + 技術條件命中"
    )

    if shares:
        print(f"✅ 擠壓策略建倉成功：{shares} 股，用資金 ${capital_used:.2f}")
    return shares, capital_used
