# ✅ 指標快取模組，用於出場時回填 RSI / OBV 等
indicator_cache = {}

def cache_indicators(symbol, indicators):
    indicator_cache[symbol] = indicators

def get_cached_indicators(symbol):
    return indicator_cache.get(symbol, {})
