"""多数据源净值获取：天天基金 → 东方财富 → akshare 自动 fallback"""
import re
import time
import json
from typing import Optional

import httpx


# 基金代码映射：解决部分基金在天天基金系统无数据的问题
FUND_CODE_MAPPING = {
    "513186": "159741",  # 嘉实恒生科技ETF → 恒生科技ETF嘉实
}


async def get_fund_nav_multi_source(fund_code: str) -> Optional[dict]:
    """
    多数据源获取基金净值，按优先级尝试：
    1. 天天基金 fundgz API (实时估值 + 单位净值)
    2. 东方财富 fund API (历史净值)
    3. akshare (备用)

    返回: {nav_date, nav, prev_nav, nav_accuracy: "confirmed"|"estimated"}
    """
    fund_code = fund_code.strip()

    # 代码映射：如果原代码无数据，尝试映射后的代码
    mapped_code = FUND_CODE_MAPPING.get(fund_code)

    # ===== 1. 天天基金 fundgz API =====
    result = await _get_nav_tiantian(fund_code)
    if result:
        return result

    # 如果原代码无数据且有映射，尝试映射后的代码
    if mapped_code:
        result = await _get_nav_tiantian(mapped_code)
        if result:
            result["mapped_from"] = fund_code
            result["actual_code"] = mapped_code
            return result

    # ===== 2. 东方财富基金净值 API =====
    result = await _get_nav_eastmoney(fund_code)
    if result:
        return result

    if mapped_code:
        result = await _get_nav_eastmoney(mapped_code)
        if result:
            result["mapped_from"] = fund_code
            result["actual_code"] = mapped_code
            return result

    # ===== 3. akshare 备用 =====
    result = await _get_nav_akshare(fund_code)
    if result:
        return result

    if mapped_code:
        result = await _get_nav_akshare(mapped_code)
        if result:
            result["mapped_from"] = fund_code
            result["actual_code"] = mapped_code
            return result

    return None


async def _get_nav_tiantian(fund_code: str) -> Optional[dict]:
    """天天基金 fundgz API：获取实时估值和最新单位净值"""
    url = f"http://fundgz.1234567.com.cn/js/{fund_code}.js"
    try:
        rt = str(int(time.time() * 1000))
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, params={"rt": rt})
            if resp.status_code != 200:
                return None
            match = re.search(r"jsonpgz\((\{.*?\})\)", resp.text)
            if not match:
                return None
            data = json.loads(match.group(1))
            return {
                "nav_date": data.get("jzrq", ""),
                "nav": float(data["dwjz"]) if data.get("dwjz") else None,
                "prev_nav": None,  # 天天基金不提供前一日净值
                "nav_accuracy": "estimated",  # 估算净值
                "source": "tiantian_fundgz",
            }
    except Exception:
        return None


async def _get_nav_eastmoney(fund_code: str) -> Optional[dict]:
    """东方财富基金净值 API：获取历史净值"""
    url = "http://api.fund.eastmoney.com/f10/lsjz"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params={
                "fundCode": fund_code,
                "pageIndex": "1",
                "pageSize": "2",
            })
            if resp.status_code != 200:
                return None
            data = resp.json()
            # 检查 Data 字段
            if not data.get("Data"):
                return None
            lsjz = data["Data"].get("LSJZList", [])
            if len(lsjz) < 1:
                return None

            latest = lsjz[0]
            prev = lsjz[1] if len(lsjz) >= 2 else None

            return {
                "nav_date": latest.get("FSRQ", ""),
                "nav": _safe_float(latest.get("DWJZ")),
                "prev_nav": _safe_float(prev.get("DWJZ")) if prev else None,
                "nav_accuracy": "confirmed",  # 确认净值
                "source": "eastmoney_lsjz",
            }
    except Exception:
        return None


async def _get_nav_akshare(fund_code: str) -> Optional[dict]:
    """akshare 备用：获取基金净值"""
    try:
        import subprocess
        result = subprocess.run(
            ['python', '-c', f'''
import akshare as ak
try:
    df = ak.fund_open_fund_info_em(symbol="{fund_code}", indicator="单位净值走势")
    if df is None or df.empty:
        print("EMPTY")
    else:
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) >= 2 else None
        nav = latest.get("单位净值")
        prev_nav = prev.get("单位净值") if prev is not None else None
        nav_date = str(latest.get("净值日期", ""))
        print(f"{nav_date}|{nav}|{prev_nav}")
except Exception as e:
    print(f"ERROR: {e}")
            '''],
            capture_output=True, text=True, timeout=20
        )
        output = result.stdout.strip()
        if output.startswith("EMPTY") or output.startswith("ERROR"):
            return None
        parts = output.split("|")
        if len(parts) >= 3:
            return {
                "nav_date": parts[0],
                "nav": _safe_float(parts[1]),
                "prev_nav": _safe_float(parts[2]),
                "nav_accuracy": "confirmed",
                "source": "akshare",
            }
    except Exception:
        pass
    return None


def _safe_float(val) -> float | None:
    if val is None or val == "" or val == "--":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None
