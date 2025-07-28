import requests

def send_discord_message(webhook_url, message):
    try:
        payload = {"content": message}
        response = requests.post(webhook_url, json=payload)

        # 印出詳細的 HTTP 回應狀態與錯誤內容
        print(f"[DEBUG] Webhook URL：{webhook_url}")
        print(f"[DEBUG] 回傳狀態碼：{response.status_code}")
        print(f"[DEBUG] 回傳訊息：{response.text}")

        if response.status_code != 204:
            print(f"[⚠️ 警告] Discord 推播失敗 ➜ {response.status_code}")
    except Exception as e:
        print(f"[❌ 錯誤] Discord 發送異常：{e}")
