from modules.notify.build_discord_message import build_breakout_message
from modules.notify.discord_push import send_discord_message
from modules.entry.enter_position import enter_position
from modules.config.config import WEBHOOK_URL

def handle_squeeze_entry(symbol, squeeze_result, sheet_entry):  # ✅ 多一個參數
    """
    擠壓突破策略建倉流程：
    - 觸發條件：進入擠壓區後突破且符合技術指標
    - 推播：格式化訊息推送至 Discord
    - 建倉：調用 enter_position() 並寫入 Google Sheets
    """
    if not squeeze_result:
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
        ema5=squeeze_result.get("ema_5"),
        ema20=squeeze_result.get("ema_20"),
        bb_upper=squeeze_result.get("bb_upper"),
        bb_lower=squeeze_result.get("bb_lower"),
        obv=squeeze_result.get("obv"),
        vwap=squeeze_result.get("vwap"),
        roc=squeeze_result.get("roc"),
        signal_note=squeeze_result.get("signal_note") or "符合技術突破條件",
        confidence_score=squeeze_result.get("confidence_score"),
        shares=squeeze_result.get("shares"),
        capital_used=squeeze_result.get("capital_used"),
        capital_left=squeeze_result.get("capital_left")
    )
    send_discord_message(WEBHOOK_URL, msg)

    # ✅ 傳入共用 sheet
    result = enter_position(
        symbol=symbol,
        price=squeeze_result["close"],
        direction=squeeze_result["direction"],
        score=squeeze_result["score"],
        strategy_name=squeeze_result["strategy_name"],
        rsi=squeeze_result.get("rsi"),
        zscore=squeeze_result.get("zscore"),
        ema5=squeeze_result.get("ema_5"),
        ema20=squeeze_result.get("ema_20"),
        bb_upper=squeeze_result.get("bb_upper"),
        bb_lower=squeeze_result.get("bb_lower"),
        obv=squeeze_result.get("obv"),
        vwap=squeeze_result.get("vwap"),
        roc=squeeze_result.get("roc"),
        trend_score=squeeze_result.get("trend_score"),
        rrov_score=squeeze_result.get("rrov_score"),
        mean_score=squeeze_result.get("mean_score"),
        signal_note="Squeeze OFF + 技術條件命中",
        sheet_name=sheet_entry  # ✅ 傳入 worksheet
    )

    if result is None:
        print(f"❌ 無法建倉：{symbol}，enter_position 回傳 None")
        return None

    shares, capital_used, _ = result
    print(f"✅ 擠壓策略建倉成功：{shares} 股，用資金 ${capital_used:.2f}")
    return shares, capital_used
