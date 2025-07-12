# modules/squeeze/push_squeeze_alert.py

from modules.squeeze.squeeze_detector import fetch_squeeze_data
import requests

WEBHOOK_URL = "https://discord.com/api/webhooks/1389605152838647909/c2S7EkfYiFBUMF4WWNyk3XrgcsmGA1-8mqXZ19a5vXn-Ti0yY366L3h77SF7M47GOzej"

def check_and_push_squeeze(symbol):
    df = fetch_squeeze_data(symbol)

    today = df.iloc[-1]
    yesterday = df.iloc[-2]

    status_today = bool(today['squeeze_on'].item())
    status_yesterday = bool(yesterday['squeeze_on'].item())

    if status_today != status_yesterday:
        close = today['Close']
        bb_u = today['BB_upper']
        bb_l = today['BB_lower']
        kc_u = today['KC_upper']
        kc_l = today['KC_lower']
        date = df.index[-1].strftime("%Y-%m-%d")

        status_text = "Squeeze ON（進入壓縮）" if status_today else "Squeeze OFF（解除壓縮）"
        emoji = "🔴" if status_today else "🟢"

        content = f"""
📊【Squeeze 雙向訊號】

📌 股票代號：{symbol}
📈 收盤價：${close:.2f}（{date}）
{emoji} 狀態更新：{status_text}

🔵 BB區間：{bb_l:.2f} ~ {bb_u:.2f}
🟠 KC區間：{kc_l:.2f} ~ {kc_u:.2f}

📘 說明：
- ON 表示市場進入盤整壓縮，波動低
- OFF 則代表壓縮解除，可能啟動趨勢行情

#Squeeze監控 #{symbol}
"""
        requests.post(WEBHOOK_URL, json={"content": content.strip()})
    else:
        print(f"[{symbol}] Squeeze 狀態未變化 ➜ 無需推播")