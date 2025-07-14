import os

def get_project_root():
    """
    回傳專案根目錄（根據目前這個檔案的位置推斷）
    """
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
