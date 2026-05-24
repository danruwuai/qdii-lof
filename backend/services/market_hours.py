"""市场状态检测"""
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))

MARKET_HOURS = {
    "CN": [
        (9, 30, 11, 30),   # 上午
        (13, 0, 15, 0),    # 下午
    ],
    "HK": [
        (9, 30, 12, 0),
        (13, 0, 16, 0),
    ],
    "US": [
        (21, 30, 23, 59),   # 晚上
        (0, 0, 4, 0),        # 次日凌晨
    ],
    "JP": [
        (8, 0, 14, 0),       # JST 9:00-15:00 = CST 8:00-14:00
    ],
    "EU": [
        (15, 30, 23, 30),    # CET 8:30-16:30 = CST 15:30-23:30
    ],
}


def is_market_open(market: str) -> bool:
    """判断指定市场当前是否在交易时间"""
    now = datetime.now(CST)
    hours = MARKET_HOURS.get(market, [])
    weekday = now.weekday()

    # 周末休市
    if weekday >= 5 and market != "US":
        return False

    hour_min = now.hour
    minute_min = now.minute

    for start_h, start_m, end_h, end_m in hours:
        start_total = start_h * 60 + start_m
        end_total = end_h * 60 + end_m
        now_total = hour_min * 60 + minute_min

        if start_total <= now_total <= end_total:
            return True

    return False


def get_active_markets(regions: str) -> list[str]:
    """获取指定地区中当前活跃的市场"""
    if not regions:
        return []
    regions_list = regions.split("+")
    return [r for r in regions_list if is_market_open(r)]


def get_all_active_markets() -> list[str]:
    """获取所有当前活跃的市场"""
    return [m for m in MARKET_HOURS if is_market_open(m)]
