# modules/utils/strategy_utils.py

def get_strategy_match_score(strategy_name, conditions: dict):
    """
    根據條件 dict 計算命中條件數與總得分
    """
    total = len(conditions)
    matched = sum(1 for k, v in conditions.items() if v)
    score = matched / total if total > 0 else 0

    # 可加入 log 或 debug 輸出
    return {
        "strategy": strategy_name,
        "score": score,
        "matched": matched,
        "total": total,
        "conditions_met": [k for k, v in conditions.items() if v]
    }
