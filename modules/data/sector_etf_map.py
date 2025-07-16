# modules/data/sector_etf_map.py

# ✅ 11 大標準產業板塊 對應 ETF
sector_etf_map = {
    "Information Technology": {"etf": "XLK", "chinese": "資訊科技"},
    "Health Care": {"etf": "XLV", "chinese": "醫療保健"},
    "Financials": {"etf": "XLF", "chinese": "金融"},
    "Consumer Discretionary": {"etf": "XLY", "chinese": "非必需消費"},
    "Consumer Staples": {"etf": "XLP", "chinese": "必需消費"},
    "Energy": {"etf": "XLE", "chinese": "能源"},
    "Industrials": {"etf": "XLI", "chinese": "工業"},
    "Materials": {"etf": "XLB", "chinese": "原物料"},
    "Utilities": {"etf": "XLU", "chinese": "公用事業"},
    "Real Estate": {"etf": "XLRE", "chinese": "房地產"},
    "Communication Services": {"etf": "XLC", "chinese": "通訊服務"},
}

def get_etf_by_sector(sector_en: str) -> str:
    """回傳 ETF 代碼"""
    return sector_etf_map.get(sector_en, {}).get("etf")

def get_chinese_by_sector(sector_en: str) -> str:
    """回傳中文板塊名稱"""
    return sector_etf_map.get(sector_en, {}).get("chinese")
