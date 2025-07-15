import os
import pandas as pd
import json
from modules.utils.path_utils import get_project_root  # 建議統一這一行，移除重複導入

# ✅ 載入股票清單（CSV）
def load_stock_list(filepath="filtered_us_stocks_common_only.csv"):
    file_path = os.path.join(get_project_root(), filepath)
    try:
        df = pd.read_csv(file_path)
        if "symbol" in df.columns:
            return df["symbol"].dropna().tolist()
        else:
            print("❌ stock_list.csv 缺少 'symbol' 欄位")
            return []
    except Exception as e:
        print(f"❌ 無法載入股票清單：{e}")
        return []

# ✅ 載入 API 金鑰設定（JSON）
def load_api_keys(filepath="config/api_keys.json"):
    full_path = os.path.join(get_project_root(), filepath)
    try:
        with open(full_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 無法載入 API 金鑰：{e}")
        return {}
