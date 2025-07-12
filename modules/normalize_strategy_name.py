def normalize_strategy_name(name):
    if "RROV" in name:
        return "RROV"
    elif "均值" in name or "mean" in name:
        return "均值回歸"
    elif "順勢" in name:
        return "順勢策略"
    return name

# ✅ Step 3: emoji 對照表
strategy_label_map = {
    "RROV": "📊 RROV 策略",
    "均值回歸": "🎯 均值回歸策略",
    "順勢策略": "📈 順勢策略",
}

signal_note = "📌 預設訊號"