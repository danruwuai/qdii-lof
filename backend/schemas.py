from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel


# ---- Fund ----
class FundBase(BaseModel):
    code: str
    name: str
    fund_type: Optional[str] = None
    manager: Optional[str] = None
    underlying_index: Optional[str] = None
    tracking_region: Optional[str] = None

    exchange: Optional[str] = None
    trading_venue: Optional[str] = None
    can_subscribe: Optional[bool] = None
    subscribe_status: Optional[str] = None
    daily_limit: Optional[float] = None
    can_buy: Optional[bool] = None
    can_sell: Optional[bool] = None

    nav_date: Optional[date] = None
    nav: Optional[float] = None
    prev_nav: Optional[float] = None
    nav_accuracy: Optional[str] = None

    market_price: Optional[float] = None
    prev_close: Optional[float] = None
    change_pct: Optional[float] = None
    volume: Optional[float] = None


class FundPremium(BaseModel):
    estimated_nav: Optional[float] = None
    nav_type: Optional[str] = None
    premium_rate: Optional[float] = None
    calc_method: Optional[str] = None
    stale: bool = False


class FundDetail(FundBase):
    premium: Optional[FundPremium] = None
    holdings: list[dict] = []
    premium_history: list[dict] = []


class FundListItem(FundBase):
    premium: Optional[FundPremium] = None
    is_watched: bool = False
    estimated_daily_profit: Optional[float] = None
    is_high_premium: bool = False
    # 套利判断字段
    arbitrage_type: Optional[str] = None  # 溢价套利/持有者卖出/折价埋伏/低溢价埋伏
    net_profit: Optional[float] = None     # 扣费后预估收益(%)
    risk_tags: list[str] = []             # T+2延迟/限额极低/高波动/低流动性


class FundListResponse(BaseModel):
    items: list[FundListItem]
    total: int


# ---- Watchlist ----
class WatchlistItem(BaseModel):
    fund_code: str


class WatchlistResponse(BaseModel):
    items: list[FundListItem]


# ---- Alert ----
class AlertCreate(BaseModel):
    fund_code: str
    threshold_above: Optional[float] = None
    threshold_below: Optional[float] = None


class AlertUpdate(BaseModel):
    threshold_above: Optional[float] = None
    threshold_below: Optional[float] = None
    is_active: Optional[bool] = None


class AlertResponse(BaseModel):
    id: int
    fund_code: str
    threshold_above: Optional[float]
    threshold_below: Optional[float]
    is_active: bool

    model_config = {"from_attributes": True}


# ---- Market Status ----
class MarketStatus(BaseModel):
    cn: str       # open / closed / pre
    hk: str
    us: str
    jp: str
    eu: str
    timestamp: str
