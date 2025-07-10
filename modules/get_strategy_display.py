def get_strategy_display(name):
    return strategy_label_map.get(normalize_strategy_name(name), "📌 未知策略")