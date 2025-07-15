import requests
from modules.config import WEBHOOK_URL  # ✅ 加這行，從 config 匯入 webhook

def send_discord_message(message, webhook_url):
    import requests
    payload = {"content": message}
    response = requests.post(webhook_url, json=payload)
    if response.status_code != 204:
        print(f"[推播錯誤] Discord webhook 回傳 {response.status_code}：{response.text}")
