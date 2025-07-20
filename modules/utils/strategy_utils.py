# modules/utils/strategy_utils.py

def get_strategy_match_score(strategy_name, conditions: dict):
    """
    根據條件 dict 計算命中條件數與總得分（回傳詳細 dict + int_score）
    """
    total = len(conditions)
    matched = sum(1 for k, v in conditions.items() if v)
    ratio = matched / total if total > 0 else 0

    # 轉成 0~3 分
    if ratio >= 1.0:
        int_score = 3
    elif ratio >= 0.66:
        int_score = 2
    elif ratio >= 0.33:
        int_score = 1
    else:
        int_score = 0

    return {
        "strategy": strategy_name,
        "score": ratio,             # 比例 0~1
        "int_score": int_score,     # 分數 0~3（⚠️ 用這個排序）
        "matched": matched,
        "total": total,
        "conditions_met": [k for k, v in conditions.items() if v]
    }
