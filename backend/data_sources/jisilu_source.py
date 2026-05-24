"""集思录数据源：QDII/LOF/ETF 申购状态、限额、溢价率（使用 Playwright 自动获取）

集思录 QDII 页面有三个板块：
- 欧美指数 (E): /data/qdii/qdii_list/E
- 亚洲指数 (A): /data/qdii/qdii_list/A
- 商品 (C): /data/qdii/qdii_list/C (需登录)
"""
from typing import Optional


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
    # 多行文本中先提取第一个数字（通常是申购起点）
    import re
    match = re.search(r'(\d+\.?\d*)\s*(元|万|万元|亿)', s)
    if match:
        num = float(match.group(1))
        unit = match.group(2)
        if unit == "万" or unit == "万元":
            num *= 10000
        elif unit == "亿":
            num *= 100000000
        # 如果文本中明确有"无限额"且无其他限制，返回 None
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


def _process_cell(cell: dict) -> dict:
    """处理单行 cell 数据，返回标准化记录"""
    apply_status = cell.get("apply_status", "")
    redeem_status = cell.get("redeem_status", "")
    status, enable_gr = _parse_status(apply_status, redeem_status)

    min_amt = cell.get("min_amt")
    limit_amount = _parse_limit_amount(min_amt)

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
        "qtype": cell.get("qtype", ""),
        "lof_type": cell.get("lof_type", ""),
    }


async def fetch_qdii_all_sections(cookie: str = "") -> list[dict]:
    """获取集思录所有板块的 QDII/ETF 数据（欧美+亚洲+商品）"""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return []

    all_rows = []
    api_data = {}

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
            )

            # 如果提供了 cookie，注入到浏览器上下文中
            if cookie:
                # cookie 格式为分号分隔的 "name=value" 字符串
                cookies_list = []
                for c in cookie.split(";"):
                    c = c.strip()
                    if not c or "=" not in c:
                        continue
                    name, value = c.split("=", 1)
                    cookies_list.append({
                        "name": name.strip(),
                        "value": value.strip(),
                        "domain": ".jisilu.cn" if name.strip().startswith("Hm") or name.strip().startswith("HMAC") else "www.jisilu.cn",
                        "path": "/",
                    })
                if cookies_list:
                    await context.add_cookies(cookies_list)

            page = await context.new_page()

            async def handle_response(response):
                if "qdii_list" in response.url:
                    try:
                        body = await response.json()
                        url_key = response.url.split("?")[0]
                        api_data[url_key] = body
                    except Exception:
                        pass

            page.on("response", handle_response)

            # 拦截 API 请求，增大 rp 参数以获取所有行
            async def handle_route(route, request):
                if "qdii_list" in request.url:
                    url = request.url
                    if "rp=" in url:
                        url = url.replace("rp=20", "rp=500")
                    else:
                        url += "&rp=500"
                    await route.continue_(url=url)
                else:
                    await route.continue_()

            await page.route("**/data/qdii/qdii_list/*", handle_route)

            # 加载页面（默认触发 E 和 C）
            await page.goto("https://www.jisilu.cn/data/qdii/", wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(5000)

            # 直接调用 JS 函数触发 A 板块
            await page.evaluate("showQDIIA()")
            await page.wait_for_timeout(8000)

            await browser.close()

    except Exception as e:
        print(f"[集思录] 获取失败: {e}")

    # 汇总所有板块
    for url, data in api_data.items():
        rows = data.get("rows", [])
        # 从 URL 路径提取板块标识
        qtype = url.split("/")[-1]
        print(f"[集思录] {qtype}板块: {len(rows)} 只")
        all_rows.extend(rows)

    # 去重 + 标准化
    records = []
    seen = set()
    for row in all_rows:
        cell = row.get("cell", {})
        fid = cell.get("fund_id")
        if fid and fid not in seen:
            seen.add(fid)
            records.append(_process_cell(cell))

    return records


async def fetch_qdii_list(cookie: str = "") -> list[dict]:
    """获取集思录 QDII 列表（兼容旧接口，调用全量获取）"""
    return await fetch_qdii_all_sections(cookie)


async def fetch_lof_list(cookie: str = "") -> list[dict]:
    """获取集思录 LOF 列表（需要登录 cookie）"""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return []

    all_rows = []
    api_data = {}

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
            )

            # 注入 cookie
            if cookie:
                cookies_list = []
                for c in cookie.split(";"):
                    c = c.strip()
                    if not c or "=" not in c:
                        continue
                    name, value = c.split("=", 1)
                    cookies_list.append({
                        "name": name.strip(),
                        "value": value.strip(),
                        "domain": ".jisilu.cn" if name.strip().startswith("Hm") or name.strip().startswith("HMAC") else "www.jisilu.cn",
                        "path": "/",
                    })
                if cookies_list:
                    await context.add_cookies(cookies_list)

            page = await context.new_page()

            # 拦截 API 请求，增大 rp 参数
            async def handle_route(route, request):
                if "lof_list" in request.url or "stock_lof_list" in request.url or "index_lof_list" in request.url:
                    url = request.url
                    if "rp=20" in url:
                        url = url.replace("rp=20", "rp=500")
                    elif "rp=25" in url:
                        url = url.replace("rp=25", "rp=500")
                    else:
                        url += "&rp=500"
                    await route.continue_(url=url)
                else:
                    await route.continue_()

            await page.route("**/data/lof/*", handle_route)

            async def handle_response(response):
                if "lof_list" in response.url or "stock_lof_list" in response.url or "index_lof_list" in response.url:
                    try:
                        body = await response.json()
                        url = response.url.split("?")[0]
                        # 给每个 row 标记来源 URL
                        for row in body.get("rows", []):
                            row["__url__"] = url
                        api_data[url] = body
                    except Exception:
                        pass

            page.on("response", handle_response)

            await page.goto("https://www.jisilu.cn/data/lof/", wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(5000)

            # 点击"指数LOF" tab 触发第二个 API
            index_tab = await page.query_selector('a:has-text("指数LOF")')
            if index_tab:
                await index_tab.click()
                await page.wait_for_timeout(5000)

            await browser.close()

    except Exception as e:
        print(f"[集思录] LOF 获取失败: {e}")

    for url, data in api_data.items():
        rows = data.get("rows", [])
        name = "股票LOF" if "stock_lof" in url else "指数LOF"
        print(f"[集思录] {name}: {len(rows)} 只")
        all_rows.extend(rows)

    records = []
    seen = set()
    for row in all_rows:
        cell = row.get("cell", {})
        fid = cell.get("fund_id")
        # 根据来源 URL 判断 LOF 类型
        src_url = row.get("__url__", "")
        lof_type = "指数LOF" if "index_lof" in src_url else "股票LOF"
        if fid and fid not in seen:
            seen.add(fid)
            apply_status = cell.get("apply_status", "")
            redeem_status = cell.get("redeem_status", "")
            status, enable_gr = _parse_status(apply_status, redeem_status)
            min_amt = cell.get("min_amt")
            limit_amount = _parse_limit_amount(min_amt)

            records.append({
                "fund_code": fid,
                "name": cell.get("fund_nm", ""),
                "lof_type": lof_type,
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
                "qtype": cell.get("qtype", ""),
            })

    return records
