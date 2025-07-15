import os

# === 💰 資金與風控參數 ===
DEFAULT_TAKE_PROFIT = 5.0  # 鎖利門檻（例如 +5%）
DEFAULT_STOP_LOSS = 3.0            # ➤ 停損（百分比）
DEFAULT_TAKE_PROFIT = 5.0          # ➤ 第一段鎖利
TRAIL_TRIGGER = 8.0                # ➤ 第二段鎖利啟動點
TRAIL_MARGIN = 1.5                 # ➤ 回落百分比觸發出場
capital_left = 100000              # ➤ 初始資金（美元）

# === 🔗 Discord Webhook ===
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK") or "https://your-default-webhook-url"

# === 📊 Polygon API 金鑰 ===
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY") or "your-polygon-api-key"

# === 📄 Google Sheets 設定 ===
GSHEET_URL = os.getenv("GSHEET_URL") or "https://docs.google.com/spreadsheets/xxx"
GSHEET_KEY_BASE64 = os.getenv("GCP_KEY_BASE64") or None  # base64 編碼的 GCP 憑證內容
