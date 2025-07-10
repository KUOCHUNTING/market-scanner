# modules/notify/discord_push.py
import requests

def send_discord_message(webhook_url, message, silent=False):
    """
    傳送 Discord 訊息
    :param webhook_url: Discord Webhook URL
    :param message: 要傳送的文字內容
    :param silent: 若為 True，則不顯示錯誤訊息（例如用於背景任務）
    """
    payload = {"content": message}
    try:
        response = requests.post(webhook_url, json=payload)
        if response.status_code != 204:
            if not silent:
                print(f"[❌] Discord 推播失敗 ({response.status_code}) ➜ {response.text}")
    except Exception as e:
        if not silent:
            print(f"[EXCEPTION] Discord 推播錯誤：{e}")
