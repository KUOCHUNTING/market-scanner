def safe_round(value, decimals=2):
    try:
        return round(float(value), decimals)
    except (TypeError, ValueError):
        return "N/A"