# modules/indicator_cache.py

# 指標快取：避免出場階段重算所有技術指標
indicator_cache = {}

def set_cached_indicators(symbol, indicators):
    """
    快取技術指標，在建倉或掃描階段設定。
    """
    indicator_cache[symbol] = indicators

def get_cached_indicators(symbol):
    """
    讀取技術指標快取，在出場階段使用。
    若無資料，回傳空 dict。
    """
    return indicator_cache.get(symbol, {})
