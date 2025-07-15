import os
import ast

# === 設定目錄路徑 ===
strategy_dir = "modules/strategy"
init_path = os.path.join(strategy_dir, "__init__.py")

# === 要排除的模組（不導入）===
EXCLUDE_FILES = {"__init__.py", "__pycache__"}

# === 用於收集所有要導出的項目 ===
import_lines = []

for filename in os.listdir(strategy_dir):
    if not filename.endswith(".py") or filename in EXCLUDE_FILES:
        continue

    module_name = filename[:-3]
    file_path = os.path.join(strategy_dir, filename)

    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()

    try:
        tree = ast.parse(source)
        function_names = [
            node.name for node in tree.body
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
        ]

        if function_names:
            joined = ", ".join(function_names)
            import_lines.append(f"from .{module_name} import {joined}")
    except Exception as e:
        print(f"❌ 錯誤：無法解析 {filename}：{e}")

# === 寫入 __init__.py ===
with open(init_path, "w", encoding="utf-8") as f:
    f.write("# 自動生成的 __init__.py\n")
    f.write("\n".join(import_lines))

print(f"✅ 已重建：{init_path}")
