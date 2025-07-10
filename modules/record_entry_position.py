from datetime import datetime

def record_entry_position(symbol, price, direction, shares, strategy_name,
                          confidence_score=None, capital_used=None):
    """
    建倉紀錄函數，用於儲存已進場部位資訊。
    """
    entry = {
        "symbol": symbol,
        "price": price,
        "direction": direction,
        "shares": shares,
        "strategy": strategy_name,
        "confidence": confidence_score,
        "capital_used": capital_used,
        "entry_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    positions[symbol] = entry
    print(f"[✅紀錄] 已建倉：{symbol} @ ${price:.2f}｜方向：{direction}｜股數：{shares}｜策略：{strategy_name}")
