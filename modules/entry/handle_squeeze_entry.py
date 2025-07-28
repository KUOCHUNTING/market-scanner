from modules.entry.enter_position import enter_position
from modules.notify.build_discord_message import build_breakout_message
from modules.notify.discord_push import send_discord_message
from modules.config.config import WEBHOOK_URL
import os
from dotenv import load_dotenv
load_dotenv()
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

def handle_squeeze_entry(symbol, squeeze_result, sheet=None):
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
        roc=squeeze_result.get("roc"),
        obv=squeeze_result.get("obv"),
        vwap=squeeze_result.get("vwap"),
        ema5=squeeze_result.get("ema5"),
        ema20=squeeze_result.get("ema20"),
        bb_upper=squeeze_result.get("bb_upper"),
        bb_lower=squeeze_result.get("bb_lower"),
    )
    send_discord_message(msg, WEBHOOK_URL)
    
    # ✅ 進行建倉
    result = enter_position(
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
        signal_note="擠壓突破",
        signal_type="breakout",
        strategy_type="squeeze",
        sheet=sheet  # ✅ 傳入 Google Sheets 物件
    )

    return result
