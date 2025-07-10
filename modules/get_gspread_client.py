def get_gspread_client(base64_key):

    keyfile_dict = json.loads(base64.b64decode(base64_key))
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(keyfile_dict, scopes=scopes)
    return gspread.Client(auth=creds)