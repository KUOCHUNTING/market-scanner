def compute_confidence_score(rsi, roc, obv, vwap_deviation, zscore, bb_deviation, ema5, ema20):
    score = 0

    # ✅ RSI
    if rsi < 30:
        score += 0.3
    elif rsi < 40:
        score += 0.2
    elif rsi < 50:
        score += 0.1

    # ✅ ROC
    if roc > 1:
        score += 0.3
    elif roc > 0:
        score += 0.2

    # ✅ OBV
    if obv > 0:
        score += 0.2

    # ✅ EMA 趨勢
    if ema5 > ema20:
        score += 0.2

    # ✅ VWAP 貼近
    if abs(vwap_deviation) < 1.0:
        score += 0.1

    # ✅ Z-score 越偏離越加分
    if abs(zscore) > 2:
        score += 0.3
    elif abs(zscore) > 1.5:
        score += 0.2
    elif abs(zscore) > 1:
        score += 0.1

    # ✅ 布林乖離加分（>0 表示上穿、<0 表示跌破下緣）
    if bb_deviation < -2:
        score += 0.3
    elif bb_deviation < -1:
        score += 0.2
    elif bb_deviation > 2:
        score += 0.3
    elif bb_deviation > 1:
        score += 0.2

    return min(score, 1.0)

# modules/compute_confidence_score.py

def get_strategy_match_score(symbol, strategy_type):
    """
    模擬：根據策略名稱，回傳 (long 命中率, short 命中率)
    未來可以從真實資料統計得出
    """
    if strategy_type == "RROV":
        return 0.66, 0.52
    elif strategy_type == "趨勢":
        return 0.61, 0.47
    elif strategy_type == "均值":
        return 0.57, 0.56
    else:
        return 0.50, 0.50
