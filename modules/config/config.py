import os

# ✅ Discord Webhook
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK") or "https://your-default-webhook-url"

# ✅ Polygon API 金鑰
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY") or "your-polygon-api-key"

# ✅ Google Sheets 設定
GSHEET_URL = os.getenv("GSHEET_URL")
GSHEET_KEY_BASE64 = os.getenv("GCP_KEY_BASE64")

# ✅ 初始資金設定
capital_left = 100000
