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