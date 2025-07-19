# modules/exit/should_exit.py

def should_exit(entry_price, current_price, position: dict, take_profit=0.08, stop_loss=0.03):
    """
    判斷是否達到停利或停損，回傳 (True/False, 原因)
    """
    direction = position.get("direction", "多")
    if direction == "多":
        return_rate = (current_price - entry_price) / entry_price
    else:
        return_rate = (entry_price - current_price) / entry_price

    if return_rate >= take_profit:
        return True, "✅ 達到停利目標"
    elif return_rate <= -stop_loss:
        return True, "⚠️ 達到停損限制"
    else:
        return False, ""
