# modules/notify/discord_push.py

import os
import requests

DEFAULT_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

def send_discord_message(message, webhook_url=None):
    """
    傳送訊息至 Discord Webhook。
    - 支援預設 Webhook（從環境變數讀取）
    - 自動處理錯誤訊息與回應解析
    """
    if webhook_url is None:
        webhook_url = os.getenv("DISCORD_WEBHOOK")  # ✅ 修正這行！

    print(f"[DEBUG] send_discord_message() 用的 webhook_url：{webhook_url}")

    # ✅ 安全性檢查
    if not webhook_url or "discord.com/api/webhooks" not in webhook_url:
        print("[❌ 錯誤] Webhook URL 無效或未設定")
        return

    payload = {"content": message}
    
    try:
        response = requests.post(webhook_url, json=payload)
        if response.status_code == 204:
            print(f"[✅ Discord 推播成功]")
        else:
            print(f"[❌ Discord 推播失敗] 狀態碼 {response.status_code} ➜ {response.text}")
    except Exception as e:
        print(f"[❌ Discord 推播錯誤] 解析失敗：{e}")
