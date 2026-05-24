"""监控列表 CRUD API"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from models import UserWatchlist, Fund
from schemas import WatchlistItem, WatchlistResponse, FundListItem
from services.premium_service import get_cached_premium

router = APIRouter(prefix="/api/v1/watchlist", tags=["watchlist"])

# 简化：使用固定 user_openid，实际应从微信认证获取
DEFAULT_USER = "default_user"


@router.get("", response_model=WatchlistResponse)
async def get_watchlist(db: Session = Depends(get_db)):
    """获取用户监控列表"""
    items = db.query(UserWatchlist).filter(UserWatchlist.user_openid == DEFAULT_USER).all()
    fund_codes = [item.fund_code for item in items]

    funds = db.query(Fund).filter(Fund.code.in_(fund_codes)).all()
    fund_map = {f.code: f for f in funds}

    result_items = []
    for item in items:
        fund = fund_map.get(item.fund_code)
        if not fund:
            continue
        premium = get_cached_premium(fund.code)
        result_items.append(FundListItem(
            code=fund.code,
            name=fund.name,
            fund_type=fund.fund_type,
            market_price=fund.market_price,
            change_pct=fund.change_pct,
            can_subscribe=fund.can_subscribe,
            subscribe_status=fund.subscribe_status,
            daily_limit=fund.daily_limit,
            trading_venue=fund.trading_venue,
            nav=fund.nav,
            nav_date=fund.nav_date,
            premium=premium,
        ))

    return WatchlistResponse(items=result_items, total=len(result_items))

@router.post("")
async def add_to_watchlist(item: WatchlistItem, db: Session = Depends(get_db)):
    """添加到监控列表"""
    existing = db.query(UserWatchlist).filter(
        UserWatchlist.user_openid == DEFAULT_USER,
        UserWatchlist.fund_code == item.fund_code,
    ).first()
    if existing:
        return {"success": True, "message": "已在监控列表中"}

    watchlist_item = UserWatchlist(user_openid=DEFAULT_USER, fund_code=item.fund_code)
    db.add(watchlist_item)
    db.commit()
    return {"success": True}


@router.delete("/{fund_code}")
async def remove_from_watchlist(fund_code: str, db: Session = Depends(get_db)):
    """从监控列表移除"""
    item = db.query(UserWatchlist).filter(
        UserWatchlist.user_openid == DEFAULT_USER,
        UserWatchlist.fund_code == fund_code,
    ).first()
    if item:
        db.delete(item)
        db.commit()
        return {"success": True}
    return {"success": False, "message": "未找到"}
