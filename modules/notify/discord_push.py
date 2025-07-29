# modules/notify/discord_push.py

import os
import requests

def send_discord_message(message: str, *, webhook_url: str = None):
    """
    Discord 推播函數，強制只能用 keyword argument 傳 webhook_url
    """
    if not isinstance(message, str):
        print(f"[❌ 錯誤] 傳入的訊息不是字串：{type(message)}")
        return

    if webhook_url is None:
        webhook_url = os.getenv("DISCORD_WEBHOOK")

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
        print(f"[❌ Discord 推播錯誤] ➜ {e}")
