"""数据源模块导出"""
from .tiantian_source import get_estimated_nav
from .eastmoney_source import get_realtime_quote, get_batch_quotes
from .akshare_source import get_etf_spot, get_lof_spot, get_fund_nav, get_fund_holdings
from .jisilu_source import fetch_qdii_list as fetch_qdii_playwright, fetch_lof_list as fetch_lof_playwright
from .jisilu_http import fetch_qdii_http, fetch_lof_http
from .nav_source import get_fund_nav_multi_source

# 双源 fallback：优先 HTTP（兼容 Cloudflare），失败则用 Playwright（本地开发）
async def fetch_qdii_list(cookie: str = "") -> list[dict]:
    """获取集思录 QDII 列表，HTTP 优先 + Playwright 降级"""
    # 尝试 HTTP 版本（无 Playwright 依赖）
    try:
        result = await fetch_qdii_http(cookie)
        if result:
            return result
    except Exception as e:
        print(f"[集思录 HTTP 失败] {e}")

    # HTTP 失败，降级到 Playwright 版本（本地开发用）
    try:
        return await fetch_qdii_playwright(cookie)
    except Exception as e:
        print(f"[集思录 Playwright 失败] {e}")
        return []


async def fetch_lof_list(cookie: str = "") -> list[dict]:
    """获取集思录 LOF 列表，HTTP 优先 + Playwright 降级"""
    try:
        result = await fetch_lof_http(cookie)
        if result:
            return result
    except Exception as e:
        print(f"[集思录 HTTP 失败] {e}")

    try:
        return await fetch_lof_playwright(cookie)
    except Exception as e:
        print(f"[集思录 Playwright 失败] {e}")
        return []


__all__ = [
    "get_estimated_nav",
    "get_realtime_quote",
    "get_batch_quotes",
    "get_etf_spot",
    "get_lof_spot",
    "get_fund_nav",
    "get_fund_holdings",
    "fetch_qdii_list",
    "fetch_lof_list",
    "get_fund_nav_multi_source",
    "fetch_qdii_http",
    "fetch_lof_http",
    "fetch_qdii_playwright",
    "fetch_lof_playwright",
]
