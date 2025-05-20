
import gspread
from oauth2client.service_account import ServiceAccountCredentials

REQUIRED_TABS = [
    "觀察多頭", "觀察空頭",
    "預警試單", "空頭預警",
    "正式進場", "空單進場",
    "共振進場", "共振空單",
    "正式出場", "空單出場"
]

def initialize_sheets():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("gcp_cred.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/14SSmjk2Ae3rqx0VyiVoVWBXpq0NVNvsLs1RWckuX4Ko/")

        existing = [w.title for w in sheet.worksheets()]
        for tab in REQUIRED_TABS:
            if tab not in existing:
                sheet.add_worksheet(title=tab, rows="100", cols="10")
                print(f"✅ 已新增分頁：{tab}")
            else:
                print(f"✔️ 已存在分頁：{tab}")
        print("✅ Google Sheets 初始化完成！")

    except Exception as e:
        print(f"❌ 初始化失敗：{e}")

if __name__ == "__main__":
    initialize_sheets()
