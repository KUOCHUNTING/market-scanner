def fetch_stock_data(symbol):
    try:
        client = RESTClient(api_key=API_KEY)
        est = timezone('US/Eastern')
        end = datetime.now(est)
        start = end - timedelta(minutes=35)

        # 轉換為 Unix 時間戳
        start_timestamp = int(start.timestamp())
        end_timestamp = int(end.timestamp())

        aggs = client.get_aggs(
            ticker=symbol,
            multiplier=5,
            timespan="minute",
            from_=start_timestamp,  # 使用 Unix 時間戳
            to=end_timestamp,        # 使用 Unix 時間戳
            limit=100,
            adjusted=True
        )

        # 打印 aggs 以檢查其內容
        print(f"[DEBUG] aggs: {aggs}")

        # 檢查 aggs 是否為 Agg 對象
        if hasattr(aggs, 'results'):
            bars = aggs.results
        else:
            bars = aggs

        if not bars or not isinstance(bars, list):
            print(f"[WARNING] 無效K線資料：{symbol}")
            return None

        data = []
        for bar in bars:
            if all(k in bar for k in ["t", "o", "h", "l", "c", "v"]):
                data.append({
                    "timestamp": pd.to_datetime(bar["t"], unit='ms'),
                    "open": bar["o"],
                    "high": bar["h"],
                    "low": bar["l"],
                    "close": bar["c"],
                    "volume": bar["v"]
                })

        df = pd.DataFrame(data)
        df.set_index("timestamp", inplace=True)
        return df
    except Exception as e:
        print(f"[ERROR] 抓取資料失敗 {symbol}：{e}")
        return None
