def connect_to_gsheet():
    b64_json = os.getenv("GCP_KEY_BASE64")
    info = json.loads(base64.b64decode(b64_json))
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    client = gspread.authorize(creds)
    return client