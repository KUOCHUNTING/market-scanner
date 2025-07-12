import os
import pandas as pd
import json
from datetime import datetime

# === 📁 路徑工具 ===
def get_project_root():
    """
    回傳專案根目錄（根據目前這個檔案的位置推斷）
    """
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# === 📊 股票清單讀取 ===
def load_stock_list(filepath="filtered_us_stocks_common_only.csv"):
    file_path = os.path.join(get_project_root(), filepath)  # ✅ 改回 filepath
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

# === 🔐 API 金鑰載入工具（可選） ===
def load_api_keys(filepath="config/api_keys.json"):
    """
    從 JSON 檔載入所有 API 金鑰，支援 FRED、Polygon、Discord Webhook 等
    檔案格式範例：
    {
        "FRED_API_KEY": "xxxxx",
        "POLYGON_API_KEY": "yyyyy",
        "DISCORD_WEBHOOK": "https://discord.com/api/webhooks/..."
    }
    """
    full_path = os.path.join(get_project_root(), filepath)
    try:
        with open(full_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 無法載入 API 金鑰：{e}")
        return {}

# === 🪵 錯誤日誌記錄 ===
def log_error(message, filename="error_log.txt"):
    """
    將錯誤訊息寫入錯誤日誌檔案中，附上時間戳記
    """
    full_path = os.path.join(get_project_root(), filename)
    with open(full_path, "a") as f:
        f.write(f"[{datetime.now()}] {message}\n")
