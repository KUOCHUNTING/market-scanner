# modules/strategy/core.py

from modules.utils.format import safe_float
from modules.utils.strategy_utils import get_strategy_match_score

# ✅ 擠壓突破偵測
def detect_squeeze_breakout(symbol):
    # ➜ 建議改為正式偵測邏輯，目前為範例資料
    result = {
        "symbol": symbol,
        "direction": "做多",
        "score": 3,
        "strategy_name": "擠壓突破",
        "close": 105.2,
        "rsi": 65.3,
        "ema_5": 104.8,
        "ema_20": 102.7
    }
    return result

# ✅ RROV 策略評分
def get_rrov_score(indicators, latest_price):
    conditions = {
        "突破壓力": latest_price > indicators['bb_upper'].iloc[-1],
        "量能放大": indicators['curr_volume'] > indicators['avg_volume'] * 1.2,
        "短期強勢": latest_price > indicators['ema_5'].iloc[-1]
    }
    return get_strategy_match_score("RROV", conditions)

# ✅ 順勢策略評分
def get_trend_score(indicators):
    conditions = {
        "RSI強勢": indicators['rsi'].iloc[-1] > 60,
        "均線多頭": indicators['ema_5'].iloc[-1] > indicators['ema_20'].iloc[-1]
    }
    return get_strategy_match_score("順勢策略", conditions)

# ✅ 均值回歸策略評分
def get_mean_score(indicators, latest_price):
    zscore = indicators['zscore'].iloc[-1]
    ema5 = indicators['ema_5'].iloc[-1]
    mean_price = indicators['ema_20'].iloc[-1]
    conditions = {
        "Z-score 超賣": zscore < -1,
        "價格低於短均": latest_price < ema5,
        "價格偏離均值": latest_price < mean_price * 0.97
    }
    return get_strategy_match_score("均值回歸", conditions)

# ✅ 技術信心分數計算
def compute_confidence_score(rsi, roc, obv, vwap_deviation, zscore, bb_deviation, ema5, ema20):
    score = 0
    if rsi > 50: score += 1
    if roc > 0: score += 1
    if obv > 0: score += 1
    if vwap_deviation < 0: score += 1
    if zscore > -1: score += 1
    if bb_deviation > 0: score += 1
    if ema5 > ema20: score += 1
    return score

# ✅ 統一策略偵測主函數
def detect_trading_signal(symbol, df, indicators, latest_price):
    candidates = []

    # ➤ 擠壓突破策略
    squeeze = detect_squeeze_breakout(symbol)
    if squeeze:
        return "squeeze_breakout", squeeze["strategy_name"], "擠壓突破觸發", squeeze["direction"], squeeze

    # ➤ RROV
    rrov_score = get_rrov_score(indicators, latest_price)
    if rrov_score >= 2:
        candidates.append(("rrov", "RROV 強勢起漲", "強勢突破", "做多", rrov_score))

    # ➤ 順勢策略
    trend_score = get_trend_score(indicators)
    if trend_score >= 2:
        candidates.append(("trend", "順勢策略", "均線與 RSI 多頭", "做多", trend_score))

    # ➤ 均值回歸
    mean_score = get_mean_score(indicators, latest_price)
    if mean_score >= 2:
        candidates.append(("mean", "均值回歸", "價格偏離均值", "做多", mean_score))

    # ➤ 選擇最佳策略
    if candidates:
        best = max(candidates, key=lambda x: x[-1])  # 依得分排序
        return best[0], best[1], best[2], best[3], None

    return None, None, None, None, None
