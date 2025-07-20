# modules/strategy/core.py

from modules.utils.format import safe_float
from modules.utils.strategy_utils import get_strategy_match_score

# ✅ 擠壓突破偵測（改為動態方向）
def detect_squeeze_breakout(symbol, indicators):
    """
    擠壓突破策略（正式邏輯）：
    條件：
        1. BB 壓縮：布林帶寬度 < 平均 × 0.8
        2. 價格突破上軌（做多）或下軌（做空）
        3. RSI 強弱判斷
        4. EMA 趨勢一致
        5. OBV > 0
        6. ROC > 0
    回傳：
        direction, score, 技術指標資訊
    """
    if indicators is None or len(indicators) < 21:
        return None

    # 取值
    close = indicators['close'].iloc[-1]
    bb_upper = indicators['bb_upper'].iloc[-1]
    bb_lower = indicators['bb_lower'].iloc[-1]
    bb_width = bb_upper - bb_lower
    avg_bb_width = (indicators['bb_upper'] - indicators['bb_lower']).rolling(window=20).mean().iloc[-1]
    ema5 = indicators['ema_5'].iloc[-1]
    ema20 = indicators['ema_20'].iloc[-1]
    rsi = indicators['rsi'].iloc[-1]
    zscore = indicators['zscore'].iloc[-1]
    roc = indicators['roc'].iloc[-1]
    obv = indicators['obv'].iloc[-1]
    vwap = indicators['vwap'].iloc[-1]

    # 1️⃣ BB 壓縮
    is_squeeze = bb_width < avg_bb_width * 0.8
    if not is_squeeze:
        return None

    # 2️⃣ 突破方向
    if close > bb_upper:
        direction = "做多"
    elif close < bb_lower:
        direction = "做空"
    else:
        return None  # 沒突破，略過

    # 3️⃣ 條件式評分（越多條件符合，score 越高）
    score = 0
    if direction == "做多":
        if rsi > 50: score += 1
        if ema5 > ema20: score += 1
        if obv > 0: score += 1
        if roc > 0: score += 1
    else:  # 做空
        if rsi < 50: score += 1
        if ema5 < ema20: score += 1
        if obv < 0: score += 1
        if roc < 0: score += 1

    # BB 壓縮與突破 ⇒ +2 分
    score += 2

    # 整理回傳格式
    result = {
        "symbol": symbol,
        "close": close,
        "direction": direction,
        "score": score,
        "strategy_name": "擠壓突破",
        "rsi": rsi,
        "zscore": zscore,
        "roc": roc,
        "obv": obv,
        "vwap": vwap,
        "ema_5": ema5,
        "ema_20": ema20,
        "bb_upper": bb_upper,
        "bb_lower": bb_lower,
    }

    return result

# ✅ RROV 策略評分（雙向）
def get_rrov_score(indicators, latest_price):
    long_conditions = {
        "突破壓力": latest_price > indicators['bb_upper'].iloc[-1],
        "量能放大": indicators['curr_volume'] > indicators['avg_volume'] * 1.2,
        "短期強勢": latest_price > indicators['ema_5'].iloc[-1]
    }

    short_conditions = {
        "跌破支撐": latest_price < indicators['bb_lower'].iloc[-1],
        "量能放大": indicators['curr_volume'] > indicators['avg_volume'] * 1.2,
        "短期疲弱": latest_price < indicators['ema_5'].iloc[-1]
    }

    # ✅ 正確取出 score
    long_score = get_strategy_match_score("RROV", long_conditions).get("score", 0)
    short_score = get_strategy_match_score("RROV", short_conditions).get("score", 0)

    if long_score >= short_score:
        return long_score, "做多"
    else:
        return short_score, "做空"

# ✅ 順勢策略評分（雙向）
def get_trend_score(indicators):
    long_conditions = {
        "RSI強勢": indicators['rsi'].iloc[-1] > 60,
        "均線多頭": indicators['ema_5'].iloc[-1] > indicators['ema_20'].iloc[-1]
    }

    short_conditions = {
        "RSI疲弱": indicators['rsi'].iloc[-1] < 40,
        "均線空頭": indicators['ema_5'].iloc[-1] < indicators['ema_20'].iloc[-1]
    }

    long_score = get_strategy_match_score("順勢策略", long_conditions).get("score", 0)
    short_score = get_strategy_match_score("順勢策略", short_conditions).get("score", 0)

    if long_score >= short_score:
        return long_score, "做多"
    else:
        return short_score, "做空"

# ✅ 均值回歸策略評分（雙向）
def get_mean_score(indicators, latest_price):
    zscore = indicators['zscore'].iloc[-1]
    ema5 = indicators['ema_5'].iloc[-1]
    mean_price = indicators['ema_20'].iloc[-1]

    long_conditions = {
        "Z-score 超賣": zscore < -1,
        "價格低於短均": latest_price < ema5,
        "價格偏離均值": latest_price < mean_price * 0.97
    }

    short_conditions = {
        "Z-score 超買": zscore > 1,
        "價格高於短均": latest_price > ema5,
        "價格偏離均值": latest_price > mean_price * 1.03
    }

    long_score = get_strategy_match_score("均值回歸", long_conditions).get("score", 0)
    short_score = get_strategy_match_score("均值回歸", short_conditions).get("score", 0)

    if long_score >= short_score:
        return long_score, "做多"
    else:
        return short_score, "做空"

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

# ✅ 主策略偵測（整合四種策略 + 做多/做空 + 分數比較）
def detect_trading_signal(symbol, df, indicators, latest_price):
    candidates = []

    # ✅ 擠壓突破（正式版本）
    squeeze = detect_squeeze_breakout(symbol, indicators)
    squeeze_score = 0
    if squeeze:
        squeeze_score = squeeze["score"]
        candidates.append((
            "squeeze_breakout", squeeze["strategy_name"], "擠壓突破觸發",
            squeeze["direction"], squeeze_score, squeeze
        ))

    # ✅ RROV
    rrov_score, rrov_dir = get_rrov_score(indicators, latest_price)
    if rrov_score >= 2:
        candidates.append(("rrov", "RROV 強勢起漲", "強勢突破", rrov_dir, rrov_score, None))

    # ✅ 順勢
    trend_score, trend_dir = get_trend_score(indicators)
    if trend_score >= 2:
        candidates.append(("trend", "順勢策略", "趨勢同步", trend_dir, trend_score, None))

    # ✅ 均值回歸
    mean_score, mean_dir = get_mean_score(indicators, latest_price)
    if mean_score >= 2:
        candidates.append(("mean", "均值回歸", "價格偏離均值", mean_dir, mean_score, None))

    # ✅ debug 分數印出
    print(f"[DEBUG] {symbol}｜RROV: {rrov_score}｜趨勢: {trend_score}｜均值: {mean_score}｜擠壓: {squeeze_score}")

    # ✅ 選出最高分策略
    if candidates:
        best = sorted(candidates, key=lambda x: x[4], reverse=True)[0]
        signal_type, strategy_name, note, direction, score, extra = best
        return signal_type, strategy_name, note, direction, extra

    return None, None, None, None, None
