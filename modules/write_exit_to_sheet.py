def write_exit_to_sheet(
    symbol, entry_time, exit_time, return_rate, pnl, holding_minutes,
    exit_price=None,  # ✅ 新增參數
    rsi=None, zscore=None, roc=None, obv=None, vwap=None,
    ema5=None, ema20=None, strategy_name="未知策略"
):
    try:
        from datetime import datetime
        import base64, json, os, gspread
        from google.oauth2.service_account import Credentials

        keyfile_dict = json.loads(base64.b64decode(os.getenv("GOOGLE_SERVICE_ACCOUNT_BASE64")))
        scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(keyfile_dict, scopes=scopes)
        client = gspread.authorize(creds)

        sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/14SSmjk2Ae3rqx0VyiVoVWBXpq0NVNvsLs1RWckuX4Ko/edit")
        ws = sheet.worksheet("出場紀錄")  # 第二分頁

        # 組合資料列
        row = [
            entry_time.strftime("%Y-%m-%d %H:%M:%S") if isinstance(entry_time, datetime) else entry_time,
            exit_time.strftime("%Y-%m-%d %H:%M:%S") if isinstance(exit_time, datetime) else exit_time,
            symbol,
            f"{round(return_rate, 2)}%" if return_rate is not None else "N/A",
            f"${round(pnl, 2)}" if pnl is not None else "N/A",
            f"${round(exit_price, 2)}" if exit_price is not None else "N/A",  # ✅ 出場價格
            f"{holding_minutes}" if holding_minutes is not None else "N/A",
            round(rsi, 2) if rsi is not None else "",
            round(zscore, 2) if zscore is not None else "",
            round(roc, 2) if roc is not None else "",
            int(obv) if obv is not None else "",
            round(vwap, 2) if vwap is not None else "",
            round(ema5, 2) if ema5 is not None else "",
            round(ema20, 2) if ema20 is not None else "",
            strategy_name
        ]

        ws.append_row(row, value_input_option="USER_ENTERED")
        print(f"[✅ 出場紀錄寫入成功] {symbol}")

    except Exception as e:
        print(f"[❌ 出場紀錄寫入錯誤] {symbol} ➜ {type(e).__name__}：{e}")