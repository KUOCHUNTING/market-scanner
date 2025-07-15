from modules.utils.file_loader import load_stock_list
from modules.fetch_stock_data import fetch_stock_data
from modules.get_fundamentals import get_fundamentals

# modules/data/loaders.py

import os
import pandas as pd

def load_stock_list():
    base_path = os.path.dirname(__file__)
    file_path = os.path.join(base_path, "filtered_us_stocks_common_only.csv")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"❌ 找不到股票清單：{file_path}")
    return pd.read_csv(file_path)
