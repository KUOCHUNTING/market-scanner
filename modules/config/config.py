import os

# ✅ Discord Webhook
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK") or "https://your-default-webhook-url"

# ✅ Polygon API 金鑰
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY") or "your-polygon-api-key"

# ✅ Google Sheets 金鑰 JSON 路徑
GCP_CREDENTIALS_PATH = os.getenv("GCP_KEY_PATH") or "config/gcp_key.json"

# ✅ 初始資金（可被 enter_position 引用）
capital_left = 100000