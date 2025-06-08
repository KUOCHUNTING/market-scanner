import gspread
from google.oauth2.service_account import Credentials

# 設定 scope + 憑證
scope = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file("gsheet_key.json", scopes=scope)

# 建立 client 並開啟 Sheet
client = gspread.authorize(creds)
sheet_id = "14SSmjk2Ae3rqx0VyiVoVWBXpq0NVNvsLs1RWckuX4Ko"
sheet = client.open_by_key(sheet_id)
ws = sheet.sheet1

# 測試寫入一行資料
ws.append_row(["✅ 測試成功", "Hello", "World"])

print("[✅] 成功寫入 Google Sheet！")
