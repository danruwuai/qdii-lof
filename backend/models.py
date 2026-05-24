from datetime import datetime, date

from sqlalchemy import (
    Column, String, Float, Boolean, Date, DateTime, Integer,
    ForeignKey, Text, create_engine
)
from sqlalchemy.orm import relationship

from database import Base


class Fund(Base):
    __tablename__ = "funds"

    code = Column(String(10), primary_key=True)
    name = Column(String(100), nullable=False)
    fund_type = Column(String(20))          # QDII-ETF / LOF / ETF
    manager = Column(String(100))
    underlying_index = Column(String(100))
    underlying_index_code = Column(String(20))
    tracking_region = Column(String(50))    # US / HK / US+HK / JP / EU
    position_ratio = Column(Float, default=0.95)

    exchange = Column(String(10))           # SZ / SH
    trading_venue = Column(String(20))      # 场内 / 场外 / 场内+场外
    can_subscribe = Column(Boolean, default=True)
    subscribe_status = Column(String(50))   # 开放 / 暂停 / 限额
    daily_limit = Column(Float)             # 单日申购限额(元), NULL=无限
    can_buy = Column(Boolean, default=True)
    can_sell = Column(Boolean, default=True)

    nav_date = Column(Date)
    nav = Column(Float)
    prev_nav = Column(Float)
    nav_accuracy = Column(String(10))       # T-1 / T-2

    # Real-time market data (cached)
    market_price = Column(Float)
    prev_close = Column(Float)
    change_pct = Column(Float)
    volume = Column(Float)
    turnover = Column(Float)
    float_cap = Column(Float)

    updated_at = Column(DateTime, default=datetime.now)

    holdings = relationship("FundHolding", back_populates="fund", lazy="select")
    snapshots = relationship("PremiumSnapshot", back_populates="fund", lazy="select")


class FundHolding(Base):
    __tablename__ = "fund_holdings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fund_code = Column(String(10), ForeignKey("funds.code"))
    holding_date = Column(Date)
    asset_code = Column(String(20))
    asset_name = Column(String(100))
    asset_type = Column(String(10))         # stock / index_etf / bond
    weight = Column(Float)
    market = Column(String(5))              # US / HK / CN / JP

    fund = relationship("Fund", back_populates="holdings")


class MarketQuote(Base):
    __tablename__ = "market_quotes"

    code = Column(String(20), primary_key=True)
    price = Column(Float, nullable=False)
    prev_close = Column(Float)
    change_pct = Column(Float)
    volume = Column(Float)
    timestamp = Column(DateTime, default=datetime.now)
    market = Column(String(5))              # CN / US / HK / JP
    data_source = Column(String(20))        # eastmoney / jisilu / akshare


class PremiumSnapshot(Base):
    __tablename__ = "premium_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fund_code = Column(String(10), ForeignKey("funds.code"))
    market_price = Column(Float)
    nav_value = Column(Float)
    nav_type = Column(String(20))           # estimated / confirmed_T1 / confirmed_T2
    premium_rate = Column(Float)
    calc_method = Column(String(10))        # A / B / C
    snapshot_time = Column(DateTime, default=datetime.now)

    fund = relationship("Fund", back_populates="snapshots")


class UserWatchlist(Base):
    __tablename__ = "user_watchlist"
    __table_args__ = ()

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_openid = Column(String(64), nullable=False, index=True)
    fund_code = Column(String(10), ForeignKey("funds.code"))
    added_at = Column(DateTime, default=datetime.now)

    fund = relationship("Fund")

    __table_args__ = (
        # UniqueConstraint("user_openid", "fund_code"),
    )


class UserAlert(Base):
    __tablename__ = "user_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_openid = Column(String(64), nullable=False, index=True)
    fund_code = Column(String(10), ForeignKey("funds.code"))
    threshold_above = Column(Float)         # 溢价率 > X% 报警
    threshold_below = Column(Float)         # 溢价率 < X% 报警
    is_active = Column(Boolean, default=True)
    last_triggered_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)

    fund = relationship("Fund")
