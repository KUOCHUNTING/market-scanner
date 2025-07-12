from datetime import datetime

def filter_fundamentals(symbol, fundamentals):
    avg_volume = fundamentals.get("avg_volume", 0)
    price = fundamentals.get("price", 5)
    is_delisted = fundamentals.get("is_delisted", False)
    is_recent_earning = fundamentals.get("is_recent_earning", False)

    # ✅ 只過濾流動性太差的股票
    if avg_volume < 300_000:
        return False, "❌ 流動性過低（<30萬）不適合隔日沖"

    # ✅ 避免停牌或財報波動
    if is_delisted:
        return False, "❌ 已下市或停牌"
    if is_recent_earning:
        return False, "⚠️ 財報發布期，波動過大"

    return True, "✅ 通過（流動性良好）"
