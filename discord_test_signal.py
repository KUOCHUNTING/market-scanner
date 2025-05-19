
import requests
from datetime import datetime

DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1373309204810563604/CUhbQ6sFvtNqSsEXxw7TnnMocMyV_VwfDqr7p3iiz3lXFUkzLNZXbzdO9EEEp87pk6lE"

# Step 1: 印出啟動訊息
print("✅ 腳本啟動成功 - 測試中")
print("✅ 開始模擬假訊號推播")

# Step 2: 模擬訊號內容
fake_signal = {
    "content": "🚨 測試訊號：$FAKE 出現模擬多頭訊號 @ " + datetime.now().strftime('%Y-%m-%d %H:%M:%S')
}

# Step 3: 發送 Discord 推播
try:
    response = requests.post(DISCORD_WEBHOOK, json=fake_signal)
    if response.status_code == 204:
        print("✅ Discord 測試訊號發送成功")
    else:
        print(f"❌ 推播失敗，狀態碼: {response.status_code}, 回應: {response.text}")
except Exception as e:
    print(f"❌ 發送推播時發生錯誤: {e}")
