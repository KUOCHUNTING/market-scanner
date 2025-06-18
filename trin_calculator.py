import requests

API_KEY = "3Oa52hFieaUvTyToZudJanq39Rw9zApi"  # 👈 請替換成你的 API 金鑰
date = "2025-06-18"               # 👈 計算哪一天的資料
url = f"https://api.polygon.io/v2/aggs/grouped/locale/us/market/stocks/{date}?adjusted=true&apiKey={API_KEY}"

response = requests.get(url)
data = response.json()

if "results" not in data:
    print("❌ 無法取得資料，請檢查 API KEY 或日期")
    exit()

advancing = declining = unchanged = 0
adv_volume = decl_volume = 0

for stock in data["results"]:
    close = stock.get("c", 0)
    open_ = stock.get("o", 0)
    volume = stock.get("v", 0)

    if close > open_:
        advancing += 1
        adv_volume += volume
    elif close < open_:
        declining += 1
        decl_volume += volume
    else:
        unchanged += 1

# 避免除以 0
adv_decl_ratio = (advancing / declining) if declining > 0 else float("inf")
vol_ratio = (adv_volume / decl_volume) if decl_volume > 0 else float("inf")
trin = adv_decl_ratio / vol_ratio if vol_ratio != 0 else float("inf")

# 結果輸出
print("📊 漲跌家數統計（" + date + "）")
print("📈 上漲家數（Advancing）：", advancing)
print("📉 下跌家數（Declining）：", declining)
print("➖ 持平家數（Unchanged）：", unchanged)
print("🔢 TRIN 指數（簡化版）：", round(trin, 4))
