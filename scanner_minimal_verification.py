
import os
import time
from datetime import datetime

def main():
    print("✅ 成功啟動最小驗證版掃描器")
    print("🕒 啟動時間：", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("📦 準備開始模擬掃描（僅供驗證 Render 是否能執行 Python）")
    for i in range(3):
        print(f"🔍 模擬掃描第 {i+1} 檔 ...")
        time.sleep(1)
    print("✅ 測試結束，程式即將結束")

if __name__ == "__main__":
    main()
