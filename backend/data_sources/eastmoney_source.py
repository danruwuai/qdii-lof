"""东方财富 push2 API 数据源：实时行情"""
import httpx

EASTMONEY_PUSH_URL = "http://push2.eastmoney.com/api/qt/stock/get"

# 市场前缀: 0=深圳, 1=上海, 102=港股, 103=美股
MARKET_PREFIX = {
    "SH": "1",
    "SZ": "0",
    "HK": "116",
    "US": "105",
}

# 需要的字段
QUOTE_FIELDS = "f2,f3,f43,f44,f45,f46,f47,f48,f57,f58,f60,f169,f170"


def _get_secid(code: str, market: str = "CN") -> str:
    """生成 secid"""
    if market == "CN":
        # A 股/基金: 深圳=0, 上海=1
        if code.startswith(("5", "6")):
            return f"1.{code}"
        return f"0.{code}"
    elif market == "HK":
        return f"116.{code}"
    elif market == "US":
        return f"105.{code}"
    return f"0.{code}"


async def get_realtime_quote(code: str, market: str = "CN") -> dict | None:
    """获取单只基金/股票实时行情"""
    secid = _get_secid(code, market)
    params = {
        "secid": secid,
        "fields": QUOTE_FIELDS,
        "ut": "fa5fd1943c7b386f172d6893dbfba10b",
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(EASTMONEY_PUSH_URL, params=params)
            data = resp.json().get("data")
            if not data:
                return None
            return {
                "code": code,
                "price": data.get("f2") or data.get("f43"),
                "change_pct": data.get("f3"),
                "change_amt": data.get("f4"),
                "high": data.get("f44"),
                "low": data.get("f45"),
                "open": data.get("f46"),
                "volume": data.get("f47"),
                "turnover": data.get("f48"),
                "prev_close": data.get("f60"),
                "market_cap": data.get("f169"),
                "float_cap": data.get("f170"),
            }
    except Exception:
        return None


async def get_batch_quotes(codes: list[str], market: str = "CN") -> list[dict]:
    """批量获取行情（通过 clist API）"""
    secids = ",".join(_get_secid(c, market) for c in codes)
    url = "http://push2.eastmoney.com/api/qt/ulist.np/get"
    params = {
        "fields": QUOTE_FIELDS,
        "secids": secids,
        "ut": "fa5fd1943c7b386f172d6893dbfba10b",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            result = resp.json()
            diffs = result.get("data", {}).get("diff", [])
            quotes = []
            for item in diffs:
                quotes.append({
                    "code": item.get("f57", ""),
                    "name": item.get("f58", ""),
                    "price": item.get("f2") or item.get("f43"),
                    "change_pct": item.get("f3"),
                    "prev_close": item.get("f60"),
                    "volume": item.get("f47"),
                    "turnover": item.get("f48"),
                })
            return quotes
    except Exception:
        return []
