import difflib
import base64
import json
import gspread
from google.oauth2.service_account import Credentials

def get_credentials_from_base64(base64_key: str):
    decoded = base64.b64decode(base64_key)
    key_dict = json.loads(decoded.decode("utf-8"))
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    return Credentials.from_service_account_info(key_dict, scopes=scopes)

def connect_to_gsheet(sheet_url: str, sheet_name: str, base64_key: str):
    creds = get_credentials_from_base64(base64_key)
    client = gspread.authorize(creds)  # ✅ 舊版使用這行

    spreadsheet = client.open_by_url(sheet_url)
    sheet_names = [ws.title for ws in spreadsheet.worksheets()]
    print("📄 現有分頁：", sheet_names)

    if sheet_name not in sheet_names:
        close_matches = difflib.get_close_matches(sheet_name, sheet_names, n=3, cutoff=0.6)
        print(f"⚠️ 找不到分頁名稱：'{sheet_name}'")
        if close_matches:
            print(f"🔍 你是不是想找這些？👉 {close_matches}")
        else:
            print("🚫 找不到任何相似分頁名稱，將建立新分頁")

    try:
        worksheet = spreadsheet.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows="100", cols="20")
        print(f"🆕 分頁 {sheet_name} 不存在，已自動建立 ✅")

    return worksheet
