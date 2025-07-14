import os
from datetime import datetime
from .path_utils import get_project_root

def log_error(message, filename="error_log.txt"):
    """
    將錯誤訊息寫入錯誤日誌檔案中，附上時間戳記
    """
    full_path = os.path.join(get_project_root(), filename)
    with open(full_path, "a") as f:
        f.write(f"[{datetime.now()}] {message}\n")
