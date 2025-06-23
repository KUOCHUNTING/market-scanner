import requests
from datetime import datetime

# ✅ 你的 Webhook URL（請替換為實際部署後的 Apps Script 網址）
WEBHOOK_URL = "https://script.google.com/u/0/home/projects/1W8jUnaIL8K8cUfAIvCyFuOcyqtxiA46x6hRDsGnqZQmgog3HTUZtC1Ja/edit"

# ✅ 測試用 payload（符合你 doPost 中的欄位）
payload = {
    "strategy": "測試策略",
    "symbol": "TEST",
    "direction": "多",
    "price": 10.5,
    "shares": 100,
    "capital": 1050,
    "rsi": 32.5,
    "zscore": -2.1,
    "roc": -0.8,
    "obv": 123456,
    "vwap": 10.3,
    "confidence_score": 0.85,
    "signal_note": "🧪 測試用訊號",
    "return_rate": "",
    "holding_minutes": "",
    "pnl": ""
}

# ✅ 發送 POST 請求
try:
    res = requests.post(WEBHOOK_URL, json=payload)
    print(f"狀態碼：{res.status_code}")
    print("回應文字：", res.text)
except Exception as e:
    print("❌ 發送失敗：", e)
