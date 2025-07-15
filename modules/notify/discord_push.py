def send_discord_message(message):
    try:
        print("[推播內容] >>>\n", message)  # ✅ 加這行除錯
        data = {"content": message}
        response = requests.post(WEBHOOK_URL, json=data)
        if response.status_code != 204:
            print(f"[錯誤] Discord 推播異常：{response.status_code} ➜ {response.text}")
    except Exception as e:
        print(f"[錯誤] 發送 Discord 訊息失敗：{e}")
