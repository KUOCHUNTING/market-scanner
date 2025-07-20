import requests
from modules.config import WEBHOOK_URL

def test_discord_push():
    msg = "✅ 測試推播成功！"
    res = requests.post(WEBHOOK_URL, json={"content": msg})
    print(res.status_code, res.text)

test_discord_push()
