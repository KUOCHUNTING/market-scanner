from datetime import datetime

def main_loop():
    while True:
        symbol_list = load_stock_list()  # 確保這是回傳股票代碼清單的函數
        scan_market(symbol_list)
        time.sleep(60)

# === ✅ 程式啟動測試推播 ===
try:
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    test_msg = f"✅ **[程式啟動通知]**\n📢 已成功啟動交易掃描系統\n🕒 時間：{now}"
    print(f"[啟動] {test_msg}")
    requests.post(WEBHOOK_URL, json={"content": test_msg})
except Exception as e:
    print(f"[EXCEPTION] Discord 測試推播錯誤：{e}")
