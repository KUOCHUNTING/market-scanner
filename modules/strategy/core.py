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
    rsi = indicators['rsi'].iloc[-1]
    roc = indicators['roc'].iloc[-1]
    obv = indicators['obv'].iloc[-1]
    zscore = indicators['zscore'].iloc[-1]
    ema5 = indicators['ema_5'].iloc[-1]
    ema20 = indicators['ema_20'].iloc[-1]
    vwap = indicators['vwap'].iloc[-1]
    bb_upper = indicators['bb_upper'].iloc[-1]
    bb_lower = indicators['bb_lower'].iloc[-1]

    vwap_deviation = (latest_price - vwap) / vwap if vwap else 0
    bb_center = (bb_upper + bb_lower) / 2
    bb_deviation = (latest_price - bb_center) / (bb_upper - bb_lower) if (bb_upper - bb_lower) else 0

    score = compute_confidence_score(rsi, roc, obv, abs(vwap_deviation), zscore, bb_deviation, ema5, ema20)

    # RROV 偏向高分強勢策略，score ≥ 4 才做多，≤ 2 則做空
    if score >= 4:
        return score, "做多"
    elif score <= 2:
        return score, "做空"
    else:
        return 0, None
        
# ✅ 順勢策略評分（雙向）
def get_trend_score(indicators, close):
    rsi = indicators['rsi'].iloc[-1]
    roc = indicators['roc'].iloc[-1]
    obv = indicators['obv'].iloc[-1]
    zscore = indicators['zscore'].iloc[-1]
    ema5 = indicators['ema_5'].iloc[-1]
    ema20 = indicators['ema_20'].iloc[-1]
    vwap = indicators['vwap'].iloc[-1]
    bb_upper = indicators['bb_upper'].iloc[-1]
    bb_lower = indicators['bb_lower'].iloc[-1]

    vwap_deviation = (indicators['close'].iloc[-1] - vwap) / vwap if vwap else 0
    bb_center = (bb_upper + bb_lower) / 2
    bb_deviation = (indicators['close'].iloc[-1] - bb_center) / (bb_upper - bb_lower) if (bb_upper - bb_lower) else 0

    score = compute_confidence_score(rsi, roc, obv, abs(vwap_deviation), zscore, bb_deviation, ema5, ema20)

    # 趨勢策略：score ≥ 3 做多、≤ 2 做空
    if score >= 3:
        return score, "做多"
    elif score <= 2:
        return score, "做空"
    else:
        return 0, None

# ✅ 均值回歸策略評分（雙向）
def get_mean_score(indicators, latest_price):
    rsi = indicators['rsi'].iloc[-1]
    roc = indicators['roc'].iloc[-1]
    obv = indicators['obv'].iloc[-1]
    zscore = indicators['zscore'].iloc[-1]
    ema5 = indicators['ema_5'].iloc[-1]
    ema20 = indicators['ema_20'].iloc[-1]
    vwap = indicators['vwap'].iloc[-1]
    bb_upper = indicators['bb_upper'].iloc[-1]
    bb_lower = indicators['bb_lower'].iloc[-1]

    vwap_deviation = (latest_price - vwap) / vwap if vwap else 0
    bb_center = (bb_upper + bb_lower) / 2
    bb_deviation = (latest_price - bb_center) / (bb_upper - bb_lower) if (bb_upper - bb_lower) else 0

    score = compute_confidence_score(rsi, roc, obv, abs(vwap_deviation), zscore, bb_deviation, ema5, ema20)

    # 均值回歸偏向反向進場：score ≤ 2 做多，score ≥ 5 做空
    if score <= 2:
        return score, "做多"
    elif score >= 5:
        return score, "做空"
    else:
        return 0, None

# ✅ 技術信心分數計算
def compute_confidence_score(rsi, roc, obv, vwap_deviation, zscore, bb_deviation, ema5, ema20):
    score = 0

    # RSI 通常 > 55 才視為強勢
    if rsi > 55:
        score += 1

    # ROC > 1 表示價格變動夠強
    if roc > 1:
        score += 1

    # OBV 為正表示資金流入
    if obv > 0:
        score += 1

    # 與 VWAP 的乖離越小越好（貼近支撐），負值為佳
    if vwap_deviation < 0:
        score += 1

    # Z-score > -0.5 表示非極端低估
    if zscore > -0.5:
        score += 1

    # BB突破偏強方向時會擴張
    if bb_deviation > 0:
        score += 1

    # 短均大於長均，為基本多頭結構
    if ema5 > ema20:
        score += 1

    return score

# ✅ 主策略偵測（整合四種策略 + 做多/做空 + 分數比較）
def detect_trading_signal(symbol, df, indicators, latest_price):
    candidates = []

    # 🔻 1. 先計算技術信心分數（統一格式）
    score = compute_confidence_score(
        rsi=indicators['rsi'].iloc[-1],
        roc=indicators['roc'].iloc[-1],
        obv=indicators['obv'].iloc[-1],
        vwap_deviation=abs(latest_price - indicators['vwap'].iloc[-1]),
        zscore=indicators['zscore'].iloc[-1],
        bb_deviation=indicators['bb_upper'].iloc[-1] - indicators['bb_lower'].iloc[-1],
        ema5=indicators['ema_5'].iloc[-1],
        ema20=indicators['ema_20'].iloc[-1]
    )

    # 🔻 2. 如果信心分數太低，就直接略過這檔
    if score < 3:
        return None, None, None, None, None

    # 🔻 3. 正常策略偵測流程
    squeeze = detect_squeeze_breakout(symbol, indicators)
    squeeze_score = 0
    if squeeze:
        squeeze_score = squeeze["score"]
        candidates.append((
            "squeeze_breakout", squeeze["strategy_name"], "擠壓突破觸發",
            squeeze["direction"], squeeze_score, squeeze
        ))

    rrov_score, rrov_dir = get_rrov_score(indicators, latest_price)
    if rrov_score >= 2:
        candidates.append(("rrov", "RROV 強勢起漲", "強勢突破", rrov_dir, rrov_score, None))

    trend_score, trend_dir = get_trend_score(indicators)
    if trend_score >= 2:
        candidates.append(("trend", "順勢策略", "趨勢同步", trend_dir, trend_score, None))

    mean_score, mean_dir = get_mean_score(indicators, latest_price)
    if mean_score >= 2:
        candidates.append(("mean", "均值回歸", "價格偏離均值", mean_dir, mean_score, None))

    print(f"[DEBUG] {symbol}｜RROV: {rrov_score}｜趨勢: {trend_score}｜均值: {mean_score}｜擠壓: {squeeze_score}")

    if candidates:
        best = sorted(candidates, key=lambda x: x[4], reverse=True)[0]
        signal_type, strategy_name, note, direction, score_only, extra = best
        return signal_type, strategy_name, note, direction, extra

    return None, None, None, None, None
