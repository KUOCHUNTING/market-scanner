def write_entry_to_sheet(symbol, price, direction, shares, capital, strategy, confidence, capital_left):
    try:
        from datetime import datetime
        import base64, json, os, gspread
        from google.oauth2.service_account import Credentials

        keyfile_dict = json.loads(base64.b64decode(os.getenv("GOOGLE_SERVICE_ACCOUNT_BASE64")))
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(keyfile_dict, scopes=scopes)
        client = gspread.Client(auth=creds)

        sheet = client.open("Trading Log").worksheet("建倉紀錄")
        now = datetime.now()

        row = [
            now.strftime("%Y-%m-%d %H:%M:%S"),  # 建倉時間
            now.strftime("%Y-%m-%d"),           # 建倉日期
            symbol,
            direction,
            shares,
            capital,
            price,
            strategy,
            confidence,
            capital_left  # ✅ 新增這一欄
        ]

        sheet.insert_row(row, index=2, value_input_option="USER_ENTERED")
        print(f"[✅ 建倉寫入成功] {symbol}")
    except Exception as e:
        print(f"[❌ 建倉寫入錯誤] {symbol} ➜ {type(e).__name__}：{e}")