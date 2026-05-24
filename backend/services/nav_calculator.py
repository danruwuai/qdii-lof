"""核心净值估算引擎：Type A / B / C 三种算法"""
import asyncio
from datetime import date
from typing import Optional

from utils.index_mapper import get_index_mapping
from utils.exchange_rate import get_current_rates, get_fx_change_since
from data_sources import eastmoney_source
from data_sources.nav_source import get_fund_nav_multi_source


# 指数行情数据源映射
INDEX_QUOTES = {
    "SPX": {"code": ".INX", "market": "US", "name": "标普500"},
    "NDX": {"code": ".NDX", "market": "US", "name": "纳斯达克100"},
    "HSI": {"code": "800001", "market": "HK", "name": "恒生指数"},
    "HSCEI": {"code": "800002", "market": "HK", "name": "恒生中国企业指数"},
    "HSTECH": {"code": "800700", "market": "HK", "name": "恒生科技指数"},
    "DAX": {"code": ".GDAXI", "market": "EU", "name": "德国DAX"},
    "FTSE": {"code": ".FTSE", "market": "EU", "name": "富时100"},
    "NIKKEI225": {"code": ".N225", "market": "JP", "name": "日经225"},
    "XAU": {"code": "XAU", "market": "US", "name": "黄金"},
    "H30136": {"code": "H30136", "market": "CN", "name": "中证海外中国互联网"},
    "000300": {"code": "000300", "market": "CN", "name": "沪深300"},
    "000905": {"code": "000905", "market": "CN", "name": "中证500"},
    "000688": {"code": "000688", "market": "CN", "name": "科创50"},
}


async def get_index_change_pct(index_code: str) -> float:
    """获取指数实时涨跌幅 (%)"""
    # 简化版：实际应从数据源获取实时指数行情
    # 这里通过东方财富接口获取
    index_info = INDEX_QUOTES.get(index_code)
    if not index_info:
        return 0.0
    # 对于 A 股指数，可通过 push2 API 获取
    if index_info["market"] == "CN":
        quote = await eastmoney_source.get_realtime_quote(index_code, "CN")
        if quote:
            return quote.get("change_pct", 0.0) or 0.0
    # TODO: 港股、美股指数行情接入
    return 0.0


async def calc_type_a(
    fund_code: str,
    fund_name: str,
    nav_t2: float,
    nav_date: date,
    market_price: float,
) -> dict:
    """
    Type A：指数跟踪法
    estimated_nav = nav_t2 * (1 + index_change * position_ratio + fx_change * (1 - position_ratio))
    """
    mapping = get_index_mapping(fund_code, fund_name)
    if not mapping:
        return {"method": None, "reason": "no_index_mapping"}

    index_code = mapping["index_code"]
    position_ratio = mapping.get("position_ratio", 0.95)
    currency = mapping.get("currency", "CNY")

    # 获取指数涨跌幅
    index_change_pct = await get_index_change_pct(index_code)
    index_change = index_change_pct / 100.0 if index_change_pct else 0.0

    # 获取汇率变动
    fx_change = 0.0
    if currency != "CNY":
        fx_change = await get_fx_change_since(currency, nav_date)

    # 计算估算净值
    estimated_nav = nav_t2 * (1 + index_change * position_ratio + fx_change * (1 - position_ratio))

    # 计算溢价率
    premium_rate = (market_price - estimated_nav) / estimated_nav * 100 if estimated_nav else None

    return {
        "method": "A",
        "estimated_nav": round(estimated_nav, 4) if estimated_nav else None,
        "nav_type": "estimated",
        "premium_rate": round(premium_rate, 2) if premium_rate is not None else None,
        "index_code": index_code,
        "index_change_pct": round(index_change_pct, 2),
        "position_ratio": position_ratio,
        "fx_change": round(fx_change, 4),
    }


async def calc_type_b(
    fund_code: str,
    nav_t2: float,
    holdings: list[dict],
    market_price: float,
) -> dict:
    """
    Type B：持仓加权法
    weighted_return = sum(weight * asset_change_pct)
    estimated_nav = nav_t2 * (1 + weighted_return)
    """
    if not holdings:
        return {"method": None, "reason": "no_holdings"}

    total_weight = 0.0
    weighted_return = 0.0

    for holding in holdings:
        weight = holding.get("weight", 0)
        if not weight:
            continue
        weight_dec = weight / 100.0  # 百分比转小数
        total_weight += weight_dec

        # 获取持仓资产实时涨跌幅
        asset_code = holding.get("asset_code", "")
        market = holding.get("market", "CN")
        quote = await eastmoney_source.get_realtime_quote(asset_code, market)
        if quote:
            change = (quote.get("change_pct") or 0) / 100.0
            weighted_return += weight_dec * change

    # 如果总权重不足 60%，认为不够准确
    if total_weight < 0.6:
        return {"method": None, "reason": "low_coverage", "coverage": round(total_weight * 100, 1)}

    estimated_nav = nav_t2 * (1 + weighted_return)
    premium_rate = (market_price - estimated_nav) / estimated_nav * 100 if estimated_nav else None

    return {
        "method": "B",
        "estimated_nav": round(estimated_nav, 4) if estimated_nav else None,
        "nav_type": "estimated",
        "premium_rate": round(premium_rate, 2) if premium_rate is not None else None,
        "coverage": round(total_weight * 100, 1),
    }


async def calc_type_c(
    nav_t1: float,
    market_price: float,
) -> dict:
    """
    Type C：简单兜底
    premium_rate = (market_price - nav_t1) / nav_t1 * 100
    """
    if not nav_t1 or not market_price:
        return {"method": None, "reason": "no_nav_or_price"}

    premium_rate = (market_price - nav_t1) / nav_t1 * 100

    return {
        "method": "C",
        "estimated_nav": round(nav_t1, 4),
        "nav_type": "confirmed_T1",
        "premium_rate": round(premium_rate, 2),
    }


async def calculate_premium(
    fund_code: str,
    fund_name: str,
    nav: Optional[float],
    prev_nav: Optional[float],
    nav_date: Optional[str],
    market_price: Optional[float],
    holdings: list[dict] | None = None,
) -> dict:
    """
    统一入口：按优先级尝试 Type A → B → C
    """
    if not nav or not market_price:
        return {"method": None, "reason": "insufficient_data"}

    nav_date_obj = None
    if nav_date:
        try:
            nav_date_obj = date.fromisoformat(nav_date)
        except ValueError:
            pass

    # 尝试 Type A（带超时保护）
    if nav_date_obj:
        try:
            result_a = await asyncio.wait_for(
                calc_type_a(fund_code, fund_name, nav, nav_date_obj, market_price),
                timeout=3.0,
            )
            if result_a.get("method") == "A":
                return result_a
        except (asyncio.TimeoutError, Exception):
            pass  # Type A 失败，继续尝试 Type B/C

    # 尝试 Type B
    if holdings:
        result_b = await calc_type_b(fund_code, nav, holdings, market_price)
        if result_b.get("method") == "B":
            return result_b

    # 兜底 Type C
    use_nav = prev_nav or nav
    return await calc_type_c(use_nav, market_price)
