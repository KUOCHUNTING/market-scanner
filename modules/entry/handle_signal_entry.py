from modules.data.loaders import fetch_stock_data, load_sector_mapping
from modules.utils.helpers import get_last_value
from modules.config import POLYGON_API_KEY

# ✅ 載入產業分類
sector_map = load_sector_mapping()

def handle_signal_entry(symbol, direction, score, strategy_name,
                        signal_type, signal_note, indicators,
                        trend_score=None, rrov_score=None, mean_score=None,
                        sheet=None,
                        position_manager=None, capital_left=None):  # ✅ 共用資金控制

    # ✅ 防呆：沒傳 position_manager 就報錯
    if position_manager is None:
        raise ValueError("❌ position_manager 參數是必要的，請確認呼叫時有傳入")

    # ✅ 建倉前資金防呆檢查
    MIN_REQUIRED_CAPITAL = 3000
    if position_manager.capital_left < MIN_REQUIRED_CAPITAL:
        print(f"[略過] {symbol} ➜ 剩餘資金 ${position_manager.capital_left:.2f}，低於門檻 ${MIN_REQUIRED_CAPITAL}")
        return None

    # ✅ 抓股價資料
    df = fetch_stock_data(symbol, POLYGON_API_KEY)
    if df is None or df.empty:
        print(f"[跳過] {symbol} ➜ 無法取得價格")
        return None

    price = df["close"].iloc[-1]

    # ✅ 取得產業分類（預設為「未分類」）
    sector = sector_map.get(symbol, "未分類")
    print(f"[DEBUG] ✅ 建倉傳入 sheet: {sheet}｜sector: {sector}")

    # ✅ 呼叫 PositionManager 建倉
    result = position_manager.add_position(
        symbol=symbol,
        price=price,
        direction=direction,
        signal_note=signal_note,
        strategy_name=strategy_name,
        strategy_type=signal_type,
        signal_type=signal_type,
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
        sheet=sheet,
        sector=sector
    )

    # ✅ 建倉失敗檢查
    if result is None or result[0] is None:
        print(f"[略過] 建倉失敗 ➜ result = {result}")
        return None

    # ✅ 顯示建倉結果
    position, message, updated_capital_left = result
    shares = position["shares"]
    capital_used = position["capital_used"]

    print(f"✅ 建倉完成 ➜ {symbol}｜股數：{shares}｜資金：${capital_used:,.2f}｜剩餘：${updated_capital_left:,.2f}")
    return shares, capital_used
