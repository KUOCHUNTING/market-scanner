from modules.utils.file_loader import load_stock_list
from modules.fetch_stock_data import fetch_stock_data
from modules.get_fundamentals import get_fundamentals

# modules/data/loaders.py

import pandas as pd

def load_stock_list():
    df = pd.read_csv("modules/data/filtered_us_stocks_common_only.csv")
    return df["symbol"].dropna().unique().tolist()
