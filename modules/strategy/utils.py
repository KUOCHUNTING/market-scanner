# ✅ 策略顯示轉換：英文 → 中文 + emoji
def get_strategy_display(name):
    name = name.strip().lower()
    mapping = {
        "mean_reversion": "🎯 均值回歸",
        "trend_follow": "📈 順勢策略",
        "breakout": "🚀 突破策略",
        "rrov": "⚡ RROV 強勢起漲",
    }
    return mapping.get(name, f"📌 {name}")


# ✅ 計算策略命中分數（0~3 分）
def get_strategy_match_score(strategy_name, conditions: dict):
    """
    計算命中條件數占比（例如命中 2/3 ➜ 66%）
    回傳 0~3 的整數分數
    """
    total = len(conditions)
    matched = sum(conditions.values())
    ratio = matched / total if total > 0 else 0

    if ratio >= 1.0:
        score = 3
    elif ratio >= 0.66:
        score = 2
    elif ratio >= 0.33:
        score = 1
    else:
        score = 0

    return score
