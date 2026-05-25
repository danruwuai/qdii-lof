"""集思录数据源：HTTP API 版本（无 Playwright，兼容 Cloudflare Workers）

直接调用集思录 JSON API，通过 cookie 认证。
适用于 Cloudflare Workers 等无浏览器环境。
"""
from typing import Optional
import httpx


def _safe_float(val) -> Optional[float]:
    """安全转换浮点数"""
    if val is None or val == "" or val == "--" or val == "-":
        return None
    try:
        return float(str(val).replace("%", ""))
    except (ValueError, TypeError):
        return None


def _parse_limit_amount(min_amt) -> Optional[str]:
    """解析申购限额，返回简化后的限额字符串"""
    if min_amt is None or min_amt == "--" or min_amt == "":
        return None
    s = str(min_amt)
    import re
    match = re.search(r'(\d+\.?\d*)\s*(元|万|万元|亿)', s)
    if match:
        num = float(match.group(1))
        unit = match.group(2)
        if unit == "万" or unit == "万元":
            num *= 10000
        elif unit == "亿":
            num *= 100000000
        if "无限额" in s and "限额" not in s.replace("无限额", ""):
            return None
        return str(int(num))
    if "无限" in s or "无限额" in s:
        return None
    return s[:50]


def _parse_status(apply_status: str, redeem_status: str) -> tuple:
    """解析申购状态，返回 (status_str, enable_gr)"""
    if not apply_status or apply_status == "-":
        return "", ""
    if "暂停" in apply_status:
        return apply_status, "N"
    return apply_status, "Y"


def _process_cell(cell: dict, source_url: str = "") -> dict:
    """处理单行 cell 数据，返回标准化记录"""
    apply_status = cell.get("apply_status", "")
    redeem_status = cell.get("redeem_status", "")
    status, enable_gr = _parse_status(apply_status, redeem_status)

    min_amt = cell.get("min_amt")
    limit_amount = _parse_limit_amount(min_amt)

    # 从 URL 路径提取板块标识
    qtype = ""
    lof_type = ""
    if "/qdii_list/" in source_url:
        qtype = source_url.split("/qdii_list/")[-1]
    elif "/lof/" in source_url:
        lof_type = "股票LOF" if "stock_lof" in source_url else "指数LOF"

    return {
        "fund_code": str(cell.get("fund_id", "")),
        "name": cell.get("fund_nm", ""),
        "price": _safe_float(cell.get("price")),
        "fund_nav": _safe_float(cell.get("fund_nav")),
        "nav_date": cell.get("nav_dt", "") or cell.get("nav_dt_s", ""),
        "premium_rt": _safe_float(cell.get("nav_discount_rt")),
        "prev_nav": None,
        "prev_premium_rt": None,
        "index_increase_rt": _safe_float(cell.get("ref_increase_rt")),
        "index_name": cell.get("index_nm", ""),
        "fund_status": status,
        "enable_gr": enable_gr,
        "limit_amount": limit_amount,
        "fund_manager": cell.get("issuer_nm", ""),
        "volume": _safe_float(cell.get("volume")),
        "fund_share": _safe_float(cell.get("stock_volume")),
        "est_val_increase_rt": cell.get("est_val_increase_rt", ""),
        "estimate_value": _safe_float(cell.get("estimate_value")),
        "iopv": _safe_float(cell.get("iopv")),
        "t0": cell.get("t0", ""),
        "money_cd": cell.get("money_cd", ""),
        "qtype": qtype,
        "lof_type": lof_type,
    }


async def fetch_qdii_http(cookie: str = "") -> list[dict]:
    """
    通过 HTTP API 获取集思录 QDII 数据（欧美+亚洲+商品板块）

    Args:
        cookie: 集思录 cookie（从浏览器复制）

    Returns:
        标准化的 QDII 基金列表
    """
    all_rows = []

    # 集思录 QDII API 端点
    endpoints = [
        "https://www.jisilu.cn/data/qdii/qdii_list/E",  # 欧美
        "https://www.jisilu.cn/data/qdii/qdii_list/A",  # 亚洲
        "https://www.jisilu.cn/data/qdii/qdii_list/C",  # 商品（需要登录）
    ]

    headers = {}
    if cookie:
        headers["Cookie"] = cookie
    headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    headers["Accept"] = "application/json"
    headers["Referer"] = "https://www.jisilu.cn/"

    async with httpx.AsyncClient(timeout=15.0) as client:
        for url in endpoints:
            try:
                # 添加 rp=500 参数获取所有行
                if "rp=" not in url:
                    sep = "&" if "?" in url else "?"
                    req_url = url + f"{sep}rp=500"
                else:
                    req_url = url.replace("rp=20", "rp=500")

                resp = await client.get(req_url, headers=headers)
                if resp.status_code != 200:
                    print(f"[集思录 HTTP] {url} 返回 {resp.status_code}")
                    continue

                data = resp.json()
                rows = data.get("rows", [])
                print(f"[集思录 HTTP] {url.split('/')[-1]}板块: {len(rows)} 只")
                # 为每行记录标记来源 URL
                for row in rows:
                    row["_source_url"] = url
                all_rows.extend(rows)

            except Exception as e:
                print(f"[集思录 HTTP] {url} 失败: {e}")

    # 去重 + 标准化
    records = []
    seen = set()
    for row in all_rows:
        cell = row.get("cell", {})
        fid = cell.get("fund_id")
        source_url = row.get("_source_url", "")
        if fid and fid not in seen:
            seen.add(fid)
            records.append(_process_cell(cell, source_url=source_url))

    return records


async def fetch_lof_http(cookie: str = "") -> list[dict]:
    """
    通过 HTTP API 获取集思录 LOF 数据

    Args:
        cookie: 集思录 cookie

    Returns:
        标准化的 LOF 基金列表
    """
    all_rows = []

    endpoints = [
        "https://www.jisilu.cn/data/lof/stock_lof_list",  # 股票 LOF
        "https://www.jisilu.cn/data/lof/index_lof_list",  # 指数 LOF
    ]

    headers = {}
    if cookie:
        headers["Cookie"] = cookie
    headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    headers["Accept"] = "application/json"
    headers["Referer"] = "https://www.jisilu.cn/"

    async with httpx.AsyncClient(timeout=15.0) as client:
        for url in endpoints:
            try:
                if "rp=" not in url:
                    sep = "&" if "?" in url else "?"
                    req_url = url + f"{sep}rp=500"
                else:
                    req_url = url.replace("rp=25", "rp=500")

                resp = await client.get(req_url, headers=headers)
                if resp.status_code != 200:
                    print(f"[集思录 HTTP] {url} 返回 {resp.status_code}")
                    continue

                data = resp.json()
                rows = data.get("rows", [])
                print(f"[集思录 HTTP] {url.split('/')[-1]}: {len(rows)} 只")
                all_rows.extend(rows)

            except Exception as e:
                print(f"[集思录 HTTP] {url} 失败: {e}")

    # 去重 + 标准化
    records = []
    seen = set()
    for row in all_rows:
        cell = row.get("cell", {})
        fid = cell.get("fund_id")
        source_url = row.get("_source_url", "")
        if fid and fid not in seen:
            seen.add(fid)
            records.append(_process_cell(cell, source_url=source_url))

    return records


async def fetch_qdii_list(cookie: str = "") -> list[dict]:
    """兼容旧接口，调用 HTTP 版本"""
    return await fetch_qdii_http(cookie)


async def fetch_lof_list(cookie: str = "") -> list[dict]:
    """兼容旧接口，调用 HTTP 版本"""
    return await fetch_lof_http(cookie)
