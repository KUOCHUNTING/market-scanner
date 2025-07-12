from datetime import datetime

def write_alert_to_sheet(symbol, price, direction, signal_type, signal_note, rsi, zscore, vwap, volume_ratio):
    try:
        from datetime import datetime
        import base64, json, os, gspread
        from google.oauth2.service_account import Credentials

        # === 1. 解碼憑證
        keyfile_dict = json.loads(base64.b64decode(os.getenv("GOOGLE_SERVICE_ACCOUNT_BASE64")))
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(keyfile_dict, scopes=scopes)
        client = gspread.Client(auth=creds)

        # === 2. 打開預警紀錄分頁
        sheet = client.open("Trading Log").worksheet("預警紀錄")
        now = datetime.now()

        # === 3. 整理欄位（符合你定義的12欄格式）
        row = [
            now.strftime("%Y-%m-%d %H:%M:%S"),  # 時間
            symbol,                             # 股票代碼
            direction,                          # 多 / 空
            price,                              # 價格
            signal_type,                        # 訊號類型（ALERT_VOLUME_SPIKE_...）
            signal_note,                        # 訊號說明
            round(rsi, 2),                      # RSI
            round(zscore, 2),                   # Z-score
            round(vwap, 2),                     # VWAP
            round(volume_ratio, 2),             # 量比
            "爆量預警",                          # 策略名稱
            "預警"                                # 類別
        ]

        # === 4. 寫入最上方（第二列）
        sheet.insert_row(row, index=2, value_input_option="USER_ENTERED")
        print(f"[✅ 預警寫入成功] {symbol} ➜ {signal_type}")
    except Exception as e:
        print(f"[❌ 預警寫入錯誤] {symbol} ➜ {type(e).__name__}：{e}")
