import difflib
import base64
import json
import gspread
from google.oauth2.service_account import Credentials

def connect_with_base64_key(sheet_url, sheet_name, key_base64):
    key_dict = json.loads(base64.b64decode(gcp_key_base64).decode("utf-8"))
    creds = Credentials.from_service_account_info(key_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    client = gspread.authorize(creds)
    return client.open_by_url(sheet_url)

def get_credentials_from_base64(base64_key: str):
    decoded = base64.b64decode(base64_key)
    key_dict = json.loads(decoded.decode("utf-8"))
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    return Credentials.from_service_account_info(key_dict, scopes=scopes)

def connect_to_gsheet(sheet_url: str, sheet_name: str, base64_key: str, debug=False):  # ✅ 新增 debug 參數
    creds = get_credentials_from_base64(base64_key)
    client = gspread.authorize(creds)

    spreadsheet = client.open_by_url(sheet_url)
    sheet_names = [ws.title for ws in spreadsheet.worksheets()]

    if sheet_name not in sheet_names:
        close_matches = difflib.get_close_matches(sheet_name, sheet_names, n=3, cutoff=0.6)
        if debug:
            print(f"⚠️ 找不到分頁名稱：'{sheet_name}'")
            if close_matches:
                print(f"🔍 你是不是想找這些？👉 {close_matches}")
            else:
                print("🚫 找不到任何相似分頁名稱，將建立新分頁")

    try:
        worksheet = spreadsheet.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows="100", cols="20")

    return worksheet
