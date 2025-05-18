
import os

webhook_url = os.getenv("DISCORD_WEBHOOK")
if not webhook_url:
    print("未設定 DISCORD_WEBHOOK 環境變數")
else:
    print("成功讀取 Webhook，假裝正在推送訊號...")
    # 真正的掃描與推播邏輯可放這裡
