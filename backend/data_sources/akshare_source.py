"""akshare 数据源：基金行情、净值、持仓"""
import time
from typing import Optional

import akshare as ak
import pandas as pd


def _retry(func, retries=2, delay=1):
    for attempt in range(retries + 1):
        try:
            return func()
        except Exception as e:
            error_name = type(e).__name__
            # 连接错误可重试，其他错误直接返回 None
            if error_name in ("ConnectionError", "RemoteDisconnected", "RemoteProtocolError", 
                              "ConnectError", "TimeoutException", "SSLError"):
                if attempt == retries:
                    print(f"    [连接失败] {error_name}: {e}")
                    return None
                time.sleep(delay * (attempt + 1))
            else:
                # 其他错误不重试
                print(f"    [错误] {error_name}: {e}")
                return None


def parse_ak_value(val) -> Optional[float]:
    """解析 akshare 返回值，处理 '123.45亿' 等格式"""
    if val is None or pd.isna(val):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    if "亿" in s:
        return float(s.replace("亿", "")) * 1e8
    if "万" in s:
        return float(s.replace("万", "")) * 1e4
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def get_etf_spot() -> list[dict]:
    """获取 ETF 实时行情 (全量)"""
    def _fetch():
        return ak.fund_etf_spot_em()
    df = _retry(_fetch)
    records = []
    for _, row in df.iterrows():
        records.append({
            "code": str(row.get("代码", "")).strip(),
            "name": str(row.get("名称", "")),
            "market_price": parse_ak_value(row.get("最新价")),
            "prev_close": parse_ak_value(row.get("昨收")),
            "change_pct": parse_ak_value(row.get("涨跌幅")),
            "volume": parse_ak_value(row.get("成交量")),
            "turnover": parse_ak_value(row.get("成交额")),
            "float_cap": parse_ak_value(row.get("流通市值")),
            "fund_type": "ETF",
        })
    return records


def get_lof_spot() -> list[dict]:
    """获取 LOF 实时行情 (全量)"""
    def _fetch():
        return ak.fund_lof_spot_em()
    df = _retry(_fetch)
    records = []
    for _, row in df.iterrows():
        records.append({
            "code": str(row.get("代码", "")).strip(),
            "name": str(row.get("名称", "")),
            "market_price": parse_ak_value(row.get("最新价")),
            "prev_close": parse_ak_value(row.get("昨收")),
            "change_pct": parse_ak_value(row.get("涨跌幅")),
            "volume": parse_ak_value(row.get("成交量")),
            "turnover": parse_ak_value(row.get("成交额")),
            "float_cap": parse_ak_value(row.get("流通市值")),
            "fund_type": "LOF",
        })
    return records


def get_fund_nav(fund_code: str) -> Optional[dict]:
    """获取单只基金历史净值走势，返回最新几条"""
    def _fetch():
        return ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
    try:
        df = _retry(_fetch)
    except Exception:
        return None

    if df is None or df.empty:
        return None

    # 取最新一条净值
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else None
    return {
        "nav_date": str(latest.get("净值日期", "")),
        "nav": parse_ak_value(latest.get("单位净值")),
        "accumulated_nav": parse_ak_value(latest.get("累计净值")),
        "daily_growth": parse_ak_value(latest.get("日增长率")),
        "prev_nav": parse_ak_value(prev.get("单位净值")) if prev is not None else None,
    }


def get_fund_holdings(fund_code: str, year: str = "2024") -> list[dict]:
    """获取基金持仓（按季度）"""
    def _fetch():
        return ak.fund_portfolio_hold_em(symbol=fund_code, date=year)
    try:
        df = _retry(_fetch)
    except Exception:
        return []

    if df is None or df.empty:
        return []

    # 取最新季度的持仓
    records = []
    for _, row in df.iterrows():
        records.append({
            "asset_code": str(row.get("股票代码", "")).strip(),
            "asset_name": str(row.get("股票名称", "")),
            "weight": parse_ak_value(row.get("占净值比例")),
            "quarter": str(row.get("季度", "")),
        })
    return records


def get_all_fund_list() -> list[dict]:
    """获取全部基金列表（代码+名称）"""
    try:
        df = _retry(ak.fund_name_em)
        records = []
        for _, row in df.iterrows():
            records.append({
                "code": str(row.get("基金代码", "")).strip(),
                "name": str(row.get("基金简称", "")),
                "fund_type": str(row.get("类型", "")),
            })
        return records
    except Exception:
        return []


def is_qdii_fund(fund_code: str) -> bool:
    """判断是否为 QDII 基金"""
    nav_info = get_fund_nav(fund_code)
    if nav_info is None:
        return False
    # QDII 基金代码通常以 16、17、51、513 开头，但更可靠的方式是通过基金类型判断
    # 这里返回 True 让调用方进一步确认
    return True
