"""基金代码 → 底层指数映射（Type A 计算核心）"""
from typing import Optional

# 手动维护的 QDII/跨境 LOF 指数映射表
INDEX_MAPPING: dict[str, dict] = {
    # === 纳斯达克 ===
    "513100": {"index_code": "NDX", "index_name": "纳斯达克100", "region": "US", "position_ratio": 0.95, "currency": "USD"},
    "159941": {"index_code": "NDX", "index_name": "纳斯达克100", "region": "US", "position_ratio": 0.95, "currency": "USD"},
    "159969": {"index_code": "NDX", "index_name": "纳斯达克100", "region": "US", "position_ratio": 0.95, "currency": "USD"},
    "513300": {"index_code": "NDX", "index_name": "纳斯达克100", "region": "US", "position_ratio": 0.95, "currency": "USD"},
    "159660": {"index_code": "NDX", "index_name": "纳斯达克100", "region": "US", "position_ratio": 0.95, "currency": "USD"},
    "159632": {"index_code": "NDX", "index_name": "纳斯达克100", "region": "US", "position_ratio": 0.95, "currency": "USD"},
    "513110": {"index_code": "NDX", "index_name": "纳斯达克100", "region": "US", "position_ratio": 0.95, "currency": "USD"},
    "513390": {"index_code": "NDX", "index_name": "纳斯达克100", "region": "US", "position_ratio": 0.95, "currency": "USD"},
    "513870": {"index_code": "NDX", "index_name": "纳斯达克100", "region": "US", "position_ratio": 0.95, "currency": "USD"},
    "159509": {"index_code": "NDXT", "index_name": "纳斯达克科技", "region": "US", "position_ratio": 0.95, "currency": "USD"},
    "513290": {"index_code": "NDXBC", "index_name": "纳斯达克生物科技", "region": "US", "position_ratio": 0.95, "currency": "USD"},

    # === 标普500 ===
    "513500": {"index_code": "SPX", "index_name": "标普500", "region": "US", "position_ratio": 0.95, "currency": "USD"},
    "159655": {"index_code": "SPX", "index_name": "标普500", "region": "US", "position_ratio": 0.95, "currency": "USD"},
    "513650": {"index_code": "SPX", "index_name": "标普500", "region": "US", "position_ratio": 0.95, "currency": "USD"},
    "161125": {"index_code": "SPX", "index_name": "标普500", "region": "US", "position_ratio": 0.95, "currency": "USD"},
    "161129": {"index_code": "SPX", "index_name": "标普500", "region": "US", "position_ratio": 0.95, "currency": "USD"},
    "159529": {"index_code": "SPCONS", "index_name": "标普消费", "region": "US", "position_ratio": 0.95, "currency": "USD"},
    "513350": {"index_code": "SPGOIL", "index_name": "标普油气", "region": "US", "position_ratio": 0.95, "currency": "USD"},
    "161128": {"index_code": "SPIT", "index_name": "标普信息科技", "region": "US", "position_ratio": 0.95, "currency": "USD"},

    # === 日经225 ===
    "513000": {"index_code": "NIKKEI225", "index_name": "日经225", "region": "JP", "position_ratio": 0.95, "currency": "JPY"},
    "513520": {"index_code": "NIKKEI225", "index_name": "日经225", "region": "JP", "position_ratio": 0.95, "currency": "JPY"},
    "513880": {"index_code": "NIKKEI225", "index_name": "日经225", "region": "JP", "position_ratio": 0.95, "currency": "JPY"},
    "159866": {"index_code": "NIKKEI225", "index_name": "日经225", "region": "JP", "position_ratio": 0.95, "currency": "JPY"},

    # === 欧洲 ===
    "513030": {"index_code": "DAX", "index_name": "德国DAX", "region": "EU", "position_ratio": 0.95, "currency": "EUR"},
    "513080": {"index_code": "CAC40", "index_name": "法国CAC40", "region": "EU", "position_ratio": 0.95, "currency": "EUR"},

    # === 印度 ===
    "159513": {"index_code": "SENSEX", "index_name": "孟买SENSEX", "region": "IN", "position_ratio": 0.95, "currency": "INR"},
    "159300": {"index_code": "SENSEX", "index_name": "孟买SENSEX", "region": "IN", "position_ratio": 0.95, "currency": "INR"},
    "164824": {"index_code": "SENSEX", "index_name": "印度市场", "region": "IN", "position_ratio": 0.95, "currency": "INR"},

    # === 沙特 ===
    "159329": {"index_code": "FSTASI", "index_name": "富时沙特", "region": "SA", "position_ratio": 0.95, "currency": "SAR"},
    "520830": {"index_code": "FSTASI", "index_name": "富时沙特", "region": "SA", "position_ratio": 0.95, "currency": "SAR"},

    # === 巴西 ===
    "520870": {"index_code": "IBOV", "index_name": "巴西IBOVESPA", "region": "BR", "position_ratio": 0.95, "currency": "BRL"},
    "159100": {"index_code": "IBOV", "index_name": "巴西IBOVESPA", "region": "BR", "position_ratio": 0.95, "currency": "BRL"},

    # === 新兴亚洲/东南亚/亚太 ===
    "520580": {"index_code": "EMASIA", "index_name": "新兴亚洲", "region": "HK+IN+TW", "position_ratio": 0.95, "currency": "USD"},
    "513730": {"index_code": "EMTECH", "index_name": "东南亚科技", "region": "IN+KR+TW", "position_ratio": 0.95, "currency": "USD"},
    "159687": {"index_code": "FTAPAC", "index_name": "亚太低碳", "region": "HK+JP+AU", "position_ratio": 0.95, "currency": "USD"},

    # === 港股/恒生 ===
    "513180": {"index_code": "HSTECH", "index_name": "恒生科技", "region": "HK", "position_ratio": 0.95, "currency": "HKD"},
    "159740": {"index_code": "HSTECH", "index_name": "恒生科技", "region": "HK", "position_ratio": 0.95, "currency": "HKD"},
    "513580": {"index_code": "HSTECH", "index_name": "恒生科技", "region": "HK", "position_ratio": 0.95, "currency": "HKD"},
    "513186": {"index_code": "HSTECH", "index_name": "恒生科技", "region": "HK", "position_ratio": 0.95, "currency": "HKD"},
    "513660": {"index_code": "HSI", "index_name": "恒生指数", "region": "HK", "position_ratio": 0.95, "currency": "HKD"},
    "513690": {"index_code": "HSCEI", "index_name": "恒生中国企业", "region": "HK", "position_ratio": 0.95, "currency": "HKD"},
    "513600": {"index_code": "HSTECH", "index_name": "恒生科技", "region": "HK", "position_ratio": 0.95, "currency": "HKD"},
    "513900": {"index_code": "HSI", "index_name": "恒生指数", "region": "HK", "position_ratio": 0.95, "currency": "HKD"},

    # === 中概互联 ===
    "513050": {"index_code": "H30136", "index_name": "中证海外中国互联网", "region": "HK+US", "position_ratio": 0.95, "currency": "USD"},
    "513750": {"index_code": "H30136", "index_name": "中证海外中国互联网", "region": "HK+US", "position_ratio": 0.95, "currency": "USD"},
    "164906": {"index_code": "H30136", "index_name": "中证海外中国互联网", "region": "HK+US", "position_ratio": 0.95, "currency": "USD"},

    # === 原油/黄金 ===
    "501018": {"index_code": "WTI", "index_name": "WTI原油", "region": "US", "position_ratio": 0.95, "currency": "USD"},
    "162719": {"index_code": "WTI", "index_name": "WTI原油", "region": "US", "position_ratio": 0.95, "currency": "USD"},
    "163208": {"index_code": "WTI", "index_name": "油气能源", "region": "US", "position_ratio": 0.95, "currency": "USD"},
    "162411": {"index_code": "SPGOIL", "index_name": "标普油气", "region": "US", "position_ratio": 0.95, "currency": "USD"},
    "518880": {"index_code": "XAU", "index_name": "黄金现货", "region": "US", "position_ratio": 0.95, "currency": "USD"},

    # === 其他 LOF ===
    "162415": {"index_code": "SPCONS", "index_name": "标普美国消费", "region": "US", "position_ratio": 0.95, "currency": "USD"},
    "501312": {"index_code": "NDXT", "index_name": "海外科技", "region": "US", "position_ratio": 0.95, "currency": "USD"},
    "501300": {"index_code": "USBOND", "index_name": "美元债", "region": "US", "position_ratio": 0.95, "currency": "USD"},
    "160140": {"index_code": "DJREIT", "index_name": "美国REIT", "region": "US", "position_ratio": 0.95, "currency": "USD"},

    # === 中韩半导体 ===
    "513310": {"index_code": "KRXSEMI", "index_name": "中韩半导体", "region": "CN+KR", "position_ratio": 0.95, "currency": "USD"},
}

# 基金名称关键词 → 指数自动识别（仅跨境/QDII品种）
KEYWORD_INDEX_MAP = [
    ("纳斯达克", "NDX", "US"),
    ("纳指", "NDX", "US"),
    ("标普500", "SPX", "US"),
    ("标普消费", "SPCONS", "US"),
    ("标普油气", "SPGOIL", "US"),
    ("标普信息", "SPIT", "US"),
    ("中概互联", "H30136", "HK+US"),
    ("中国互联网", "H30136", "HK+US"),
    ("恒生科技", "HSTECH", "HK"),
    ("恒生指数", "HSI", "HK"),
    ("恒生国企", "HSCEI", "HK"),
    ("H股", "HSCEI", "HK"),
    ("日经", "NIKKEI225", "JP"),
    ("德国", "DAX", "EU"),
    ("法国", "CAC40", "EU"),
    ("富时沙特", "FSTASI", "SA"),
    ("沙特", "FSTASI", "SA"),
    ("印度", "SENSEX", "IN"),
    ("巴西", "IBOV", "BR"),
    ("新兴亚洲", "EMASIA", "HK+IN+TW"),
    ("东南亚", "EMTECH", "IN+KR+TW"),
    ("亚太", "FTAPAC", "HK+JP+AU"),
    ("黄金", "XAU", "US"),
    ("原油", "WTI", "US"),
    ("油气", "SPGOIL", "US"),
    ("美国消费", "SPCONS", "US"),
    ("海外科技", "NDXT", "US"),
    ("美元债", "USBOND", "US"),
    ("REIT", "DJREIT", "US"),
    ("半导体", "KRXSEMI", "CN+KR"),
    ("纳指科技", "NDXT", "US"),
    ("生物科技", "NDXBC", "US"),
]


def get_index_mapping(fund_code: str, fund_name: str = "") -> Optional[dict]:
    """获取基金的底层指数映射"""
    if fund_code in INDEX_MAPPING:
        return INDEX_MAPPING[fund_code]

    name = fund_name or ""
    for keyword, index_code, region in KEYWORD_INDEX_MAP:
        if keyword in name:
            return {
                "index_code": index_code,
                "index_name": keyword,
                "region": region,
                "position_ratio": 0.95,
                "currency": _guess_currency(region),
            }

    return None


def _guess_currency(region: str) -> str:
    currency_map = {
        "US": "USD", "HK": "HKD", "JP": "JPY",
        "EU": "EUR", "CN": "CNY", "HK+US": "USD",
        "IN": "INR", "SA": "SAR", "BR": "BRL",
        "HK+IN+TW": "USD", "IN+KR+TW": "USD",
        "HK+JP+AU": "USD", "CN+KR": "USD",
    }
    return currency_map.get(region, "CNY")
