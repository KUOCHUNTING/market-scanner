from modules.notify.build_discord_message import build_breakout_message
from modules.notify.discord_push import send_discord_message
from modules.entry.enter_position import enter_position
from modules.config.config import WEBHOOK_URL

def handle_squeeze_entry(symbol, squeeze_result, sheet_entry):
    """
    擠壓突破策略建倉流程：
    - 觸發條件：進入擠壓區後突破且符合技術指標
    - 推播：格式化訊息推送至 Discord
    - 建倉：調用 enter_position() 並寫入 Google Sheets
    """
    if not squeeze_result:
        return None

    print(f"📣 [{symbol}] 擠壓突破策略觸發！")

    # ✅ 資料擷取
    latest_price = squeeze_result.get("close")
    direction = squeeze_result.get("direction", "long")
    score = squeeze_result.get("score", 0)
    trend_score = squeeze_result.get("trend_score")
    rrov_score = squeeze_result.get("rrov_score")
    mean_score = squeeze_result.get("mean_score")

    indicators = {
        "rsi": squeeze_result.get("rsi"),
        "zscore": squeeze_result.get("zscore"),
        "ema5": squeeze_result.get("ema_5"),
        "ema20": squeeze_result.get("ema_20"),
        "bb_upper": squeeze_result.get("bb_upper"),
        "bb_lower": squeeze_result.get("bb_lower"),
        "obv": squeeze_result.get("obv"),
        "vwap": squeeze_result.get("vwap"),
        "roc": squeeze_result.get("roc"),
    }

    # ✅ 推播訊息組裝
    msg = build_breakout_message(
        symbol=symbol,
        price=latest_price,
        direction=direction,
        strategy_name=squeeze_result.get("strategy_name", "Squeeze Breakout"),
        score=score,
        rsi=indicators["rsi"],
        zscore=indicators["zscore"],
        ema5=indicators["ema5"],
        ema20=indicators["ema20"],
        bb_upper=indicators["bb_upper"],
        bb_lower=indicators["bb_lower"],
        obv=indicators["obv"],
        vwap=indicators["vwap"],
        roc=indicators["roc"],
        signal_note=squeeze_result.get("signal_note") or "符合技術突破條件",
        confidence_score=squeeze_result.get("confidence_score"),
        shares=squeeze_result.get("shares"),
        capital_used=squeeze_result.get("capital_used"),
        capital_left=squeeze_result.get("capital_left")
    )
    send_discord_message(WEBHOOK_URL, msg)

    # ✅ 建倉流程
    result = enter_position(
        symbol=symbol,
        price=latest_price,
        direction=direction,
        score=score,
        strategy_name="Squeeze Breakout",
        rsi=indicators["rsi"],
        zscore=indicators["zscore"],
        roc=indicators["roc"],
        obv=indicators["obv"],
        vwap=indicators["vwap"],
        ema5=indicators["ema5"],
        ema20=indicators["ema20"],
        bb_upper=indicators["bb_upper"],
        bb_lower=indicators["bb_lower"],
        signal_note="剛突破布林帶上緣",
        trend_score=trend_score,
        rrov_score=rrov_score,
        mean_score=mean_score,
        sheet=sheet_entry
    )

    if result is None:
        print(f"❌ 無法建倉：{symbol}，enter_position 回傳 None")
        return None

    shares, capital_used, _ = result
    print(f"✅ 擠壓策略建倉成功：{shares} 股，用資金 ${capital_used:.2f}")
    return position, message, capital_left
