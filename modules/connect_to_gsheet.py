# modules/connect_to_gsheet.py
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import os
import base64
import json
import gspread
from google.oauth2.service_account import Credentials

def get_credentials_from_base64(base64_key: str):
    key_data = base64.b64decode(base64_key).decode("utf-8")
    key_dict = json.loads(key_data)
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    return Credentials.from_service_account_info(key_dict, scopes=scopes)

def connect_to_gsheet(sheet_url: str, sheet_name: str, base64_key: str):
    creds = get_credentials_from_base64(base64_key)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(sheet_url).worksheet(sheet_name)
    return sheet

def write_resonance_to_sheet(timestamp, etf, sector_ch, stock_list, sheet_url, sheet_name, base64_key):
    sheet = connect_to_gsheet(sheet_url, sheet_name, base64_key)
    sheet.append_row([timestamp, etf, sector_ch, ", ".join(stock_list)])
