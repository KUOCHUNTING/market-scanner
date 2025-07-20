import os
import requests

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

def send_discord_message(message):
    payload = {"content": message}
    try:
        response = requests.post(WEBHOOK_URL, json=payload)
        if response.status_code == 204:
            print(f"[✅ Discord 推播成功]")
        else:
            print(f"[❌ Discord 推播失敗] 狀態碼 {response.status_code} ➜ {response.text}")
    except Exception as e:
        print(f"[❌ Discord 推播錯誤] {e}")
