def get_strategy_match_score(strategy_name, conditions_dict):
    total = len(conditions_dict)
    satisfied = sum(1 for cond in conditions_dict.values() if cond)

    if total == 0:
        print(f"[警告] 策略 {strategy_name} 無條件可供計算 ➜ 預設命中率為 0")
        return 0