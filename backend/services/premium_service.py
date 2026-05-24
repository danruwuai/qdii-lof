"""溢价率缓存服务"""
from typing import Optional

# 内存缓存: {fund_code: premium_data}
_premium_cache: dict[str, dict] = {}


def cache_premium(fund_code: str, data: dict):
    """缓存溢价率数据"""
    _premium_cache[fund_code] = data


def get_cached_premium(fund_code: str) -> Optional[dict]:
    """获取缓存的溢价率数据"""
    return _premium_cache.get(fund_code)


def get_all_cached_premiums() -> dict[str, dict]:
    """获取所有缓存的溢价率数据"""
    return _premium_cache.copy()


def clear_premium(fund_code: str):
    """清除单只基金缓存"""
    _premium_cache.pop(fund_code, None)


def clear_all_premiums():
    """清除所有缓存"""
    _premium_cache.clear()
