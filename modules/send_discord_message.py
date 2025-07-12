# modules/notify/discord_push.py

import requests

def send_discord_message(webhook_url, message):
    try:
        payload = {"content": message}
        response = requests.post(webhook_url, json=payload)
        if response.status_code != 204:
            print(f"[警告] Discord 推播失敗 ➜ {response.status_code}")
    except Exception as e:
        print(f"[錯誤] Discord 推播異常：{e}")
