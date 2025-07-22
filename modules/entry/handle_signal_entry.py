from modules.data.loaders import fetch_stock_data
from modules.utils.helpers import get_last_value
from modules.config import POLYGON_API_KEY, WEBHOOK_URL
from modules.notify.discord_push import send_discord_message
from modules.notify.build_discord_message import build_entry_message
from modules.entry.enter_position import enter_position
from modules.data.loaders import load_sector_mapping

sector_map = load_sector_mapping()

def handle_signal_entry(symbol, direction, score, strategy_name,
                        signal_type, signal_note, indicators,
                        trend_score=None, rrov_score=None, mean_score=None,
                        capital_left=None,
                        sheet=None):

    # ✅ 抓股價
    df = fetch_stock_data(symbol, POLYGON_API_KEY)
    if df is None or df.empty:
        print(f"[跳過] {symbol} ➜ 無法取得價格")
        return None

    price = df["close"].iloc[-1]

    # ✅ 新增 sector 對應
    sector = sector_map.get(symbol, "未分類")
    print(f"[DEBUG] ✅ 傳入 sheet: {sheet}")

    # ✅ 呼叫建倉模組
    result = enter_position(
        symbol=symbol,
        price=price,
        direction=direction,
        signal_note=signal_note,
        strategy_name=strategy_name,
        strategy_type=signal_type,
        signal_type=signal_type,
        score=score,
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
        sheet=sheet,
        sector=sector
    )

    # ✅ 建倉失敗
    if result is None or result[0] is None:
        print(f"[略過] 建倉失敗 ➜ result = {result}")
        return None

    position, message, updated_capital_left = result
    return position["shares"], position["capital_used"]
