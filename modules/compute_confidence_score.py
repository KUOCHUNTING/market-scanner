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

def get_strategy_match_score(strategy_name, conditions_dict):
    """
    根據 True/False 條件布林值，計算策略命中率
    """
    if not conditions_dict:
        return 0.0

    true_count = sum(1 for val in conditions_dict.values() if val)
    total_count = len(conditions_dict)
    
    score = round(true_count / total_count, 2)
    return score
