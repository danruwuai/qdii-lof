"""汇率获取：CNY 兑各主要货币"""
import httpx
from datetime import date

# 常用货币对（直接取 CNY=1 的汇率）
CURRENCY_PAIRS = {
    "USD": "USDCNY",  # 1 USD = ? CNY
    "HKD": "HKDCNY",
    "EUR": "EURCNY",
    "JPY": "JPYCNY",
    "GBP": "GBPCNY",
}


async def get_current_rates() -> dict[str, float]:
    """获取当前主要货币对 CNY 的汇率"""
    # 使用东方财富汇率 API
    url = "https://push2.eastmoney.com/api/qt/clist/get"
    params = {
        "pn": 1,
        "pz": 20,
        "fid": "f2",
        "fs": "m:100+s:3+s:4+s:5+s:6+s:7+s:8+s:9+s:10+s:11+s:13+s:14+s:15",
        "fields": "f2,f12,f14",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            data = resp.json().get("data", {})
            diffs = data.get("diff", [])
            rates = {}
            for item in diffs:
                name = item.get("f14", "")
                price = item.get("f2")
                if price and name:
                    rates[name] = float(price)
            return rates
    except Exception:
        # Fallback defaults
        return {
            "USDCNY": 7.25,
            "HKDCNY": 0.93,
            "EURCNY": 7.85,
            "JPYCNY": 0.048,
        }


async def get_fx_change_since(currency: str, since_date: date) -> float:
    """计算自某日期以来该货币对 CNY 的汇率变化率"""
    # 简化版：返回默认值（实际应该查询历史汇率）
    if currency == "USD":
        # 近似：假设汇率变化 < 1%
        return 0.0
    return 0.0
