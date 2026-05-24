"""基金列表/详情/搜索 API"""
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Fund, FundHolding, PremiumSnapshot, UserWatchlist
from schemas import FundListResponse, FundDetail, FundListItem, FundPremium
from services.nav_calculator import calculate_premium
from services.premium_service import get_cached_premium, get_all_cached_premiums

router = APIRouter(prefix="/api/v1/funds", tags=["funds"])

DEFAULT_USER = "default_user"
ARBITRAGE_THRESHOLD = 5.0
HIGH_PREMIUM_THRESHOLD = 10.0
ARBITRAGE_MIN_DAILY_LIMIT = 1000.0
# 费率估算：申购费0.15%（折扣平台）+ 卖出佣金0.03% = 0.18%
ARBITRAGE_FEE_RATE = 0.18


def get_watched_codes(db: Session, user: str = DEFAULT_USER) -> set:
    items = db.query(UserWatchlist.fund_code).filter(
        UserWatchlist.user_openid == user
    ).all()
    return {row[0] for row in items}


def classify_arbitrage(fund, pr: float, volume: float = None) -> dict:
    """
    基于财有道/集思录的套利逻辑分类：
    1. 溢价套利：溢价>5% 且可申购，扣除费用后有利润
    2. 持有者卖出：溢价>10% 但暂停申购，提示持有者逢高卖出
    3. 折价埋伏：折价>2%（负溢价），可买入，等溢价回归
    4. 低溢价埋伏：溢价0-3%，热门品种，等溢价拉升
    5. 溢价回落关注：溢价3-5%，从高位回落，可建仓等下一波
    """
    result = {"arbitrage_type": None, "net_profit": None, "risk_tags": []}

    if pr is None:
        return result

    net = pr - ARBITRAGE_FEE_RATE
    can_sub = fund.can_subscribe
    daily_limit = fund.daily_limit

    # QDII 份额到账延迟风险 + 到账时间标注
    if fund.fund_type and "QDII" in fund.fund_type:
        result["risk_tags"].append("T+2到账")
        # LOF 场外转场内 T+5
        if fund.fund_type.endswith("LOF"):
            result["risk_tags"].append("场外转场内T+5")
    elif fund.fund_type and "ETF" in fund.fund_type:
        # ETF 申赎门槛高，个人无法参与
        result["risk_tags"].append("ETF门槛高")
        result["risk_tags"].append("T+1到账")

    # 限额极低提示
    if can_sub and daily_limit is not None and daily_limit < ARBITRAGE_MIN_DAILY_LIMIT:
        result["risk_tags"].append("限额极低")

    # 1. 溢价套利：溢价 > 5% 且可申购
    if pr > ARBITRAGE_THRESHOLD and can_sub:
        if daily_limit is not None and daily_limit < ARBITRAGE_MIN_DAILY_LIMIT:
            return result  # 限额太低，不推荐
        result["arbitrage_type"] = "溢价套利"
        result["net_profit"] = round(net, 2)
        if pr > HIGH_PREMIUM_THRESHOLD:
            result["risk_tags"].append("高溢价波动")

    # 2. 持有者卖出：溢价 > 10% 但不可申购
    elif pr > HIGH_PREMIUM_THRESHOLD and not can_sub:
        result["arbitrage_type"] = "持有者卖出"
        result["net_profit"] = round(net, 2)
        result["risk_tags"].append("暂停申购")

    # 3. 折价埋伏：折价 > 2%
    elif pr < -2.0 and fund.can_buy is not False:
        result["arbitrage_type"] = "折价埋伏"
        result["net_profit"] = round(-pr, 2)  # 折价空间

    # 4. 低溢价埋伏：0-3% 溢价，流动性好
    elif 0 <= pr <= 3.0 and fund.can_buy is not False:
        if volume and volume > 5000:  # 成交额 > 500万
            result["arbitrage_type"] = "低溢价埋伏"
            result["net_profit"] = 0.0

    # 5. 溢价回落关注：3-5%
    elif 3.0 < pr <= ARBITRAGE_THRESHOLD and fund.can_buy is not False:
        result["arbitrage_type"] = "溢价回落"
        result["net_profit"] = round(net, 2)

    return result


def build_fund_item(fund, watched: set, tab: str = None):
    premium = get_cached_premium(fund.code)
    premium_obj = None
    pr = None
    if premium:
        premium_copy = {**premium}
        if "method" in premium_copy:
            premium_copy["calc_method"] = premium_copy.pop("method")
        premium_obj = FundPremium(**premium_copy)
        pr = premium.get("premium_rate")

    # 套利分类判断
    arb = classify_arbitrage(fund, pr, fund.volume)

    # 套利预估收益（仅套利 tab 显示）
    daily_profit = None
    if tab == "arbitrage" and pr is not None:
        if fund.daily_limit is not None:
            daily_profit = round((pr / 100) * fund.daily_limit, 2)
        else:
            daily_profit = round((pr / 100) * 10000, 2)

    return FundListItem(
        code=fund.code,
        name=fund.name,
        fund_type=fund.fund_type,
        manager=fund.manager,
        underlying_index=fund.underlying_index,
        tracking_region=fund.tracking_region,
        exchange=fund.exchange,
        trading_venue=fund.trading_venue,
        can_subscribe=fund.can_subscribe,
        subscribe_status=fund.subscribe_status,
        daily_limit=fund.daily_limit,
        can_buy=fund.can_buy,
        can_sell=fund.can_sell,
        nav_date=fund.nav_date,
        nav=fund.nav,
        prev_nav=fund.prev_nav,
        nav_accuracy=fund.nav_accuracy,
        market_price=fund.market_price,
        prev_close=fund.prev_close,
        change_pct=fund.change_pct,
        volume=fund.volume,
        premium=premium_obj,
        is_watched=(fund.code in watched),
        estimated_daily_profit=daily_profit,
        is_high_premium=(pr is not None and pr > HIGH_PREMIUM_THRESHOLD),
        arbitrage_type=arb["arbitrage_type"],
        net_profit=arb["net_profit"],
        risk_tags=arb["risk_tags"],
    )


def fund_passes_arbitrage_filter(fund) -> bool:
    """套利 tab 过滤：返回有套利机会的基金（包括溢价套利、持有者卖出、折价埋伏等）"""
    premium = get_cached_premium(fund.code)
    if not premium:
        return False
    pr = premium.get("premium_rate")
    if pr is None:
        return False

    # 套利机会定义：
    # 1. 溢价套利：溢价 > 5% 且可申购
    # 2. 持有者卖出：溢价 > 10% 但暂停申购
    # 3. 折价埋伏：折价 > 2%（负溢价）
    # 4. 低溢价埋伏：0-3% 溢价，流动性好
    # 5. 溢价回落：3-5% 溢价
    if pr > HIGH_PREMIUM_THRESHOLD:
        # 高溢价：溢价套利 或 持有者卖出
        return True
    elif pr > ARBITRAGE_THRESHOLD:
        # 中溢价：溢价回落
        return True
    elif pr >= 0:
        # 低溢价：低溢价埋伏（需要可申购且可买入）
        if fund.can_subscribe and fund.can_buy is not False:
            return True
    else:
        # 折价：折价埋伏（需要可买入）
        if pr < -2.0 and fund.can_buy is not False:
            return True

    return False


def fund_passes_filters(fund, can_subscribe: Optional[bool] = None, premium_level: Optional[str] = None, arbitrage_type: Optional[str] = None) -> bool:
    """通用筛选：申购状态、溢价等级、套利类型"""
    # 申购状态筛选
    if can_subscribe is not None:
        if can_subscribe and not fund.can_subscribe:
            return False
        if not can_subscribe and fund.can_subscribe:
            return False

    # 溢价等级和套利类型筛选需要 premium 数据
    if premium_level is not None or arbitrage_type is not None:
        premium = get_cached_premium(fund.code)
        pr = premium.get("premium_rate") if premium else None

        # 溢价等级筛选
        if premium_level is not None:
            if premium_level == "high" and (pr is None or pr <= 5.0):
                return False
            elif premium_level == "normal" and (pr is None or pr <= 0 or pr > 5.0):
                return False
            elif premium_level == "discount" and (pr is None or pr >= 0):
                return False

        # 套利类型筛选
        if arbitrage_type is not None:
            if arbitrage_type == "溢价套利":
                if pr is None or pr <= 5.0 or not fund.can_subscribe:
                    return False
            elif arbitrage_type == "持有者卖出":
                if pr is None or pr <= 10.0 or fund.can_subscribe:
                    return False
            elif arbitrage_type == "折价埋伏":
                if pr is None or pr >= -2.0:
                    return False
            elif arbitrage_type == "低溢价埋伏":
                if pr is None or pr < 0 or pr > 3.0:
                    return False
            elif arbitrage_type == "溢价回落":
                if pr is None or pr <= 3.0 or pr > 5.0:
                    return False

    return True


def build_premium_sort_key(item, tab: str = None, sort: str = "premium_rate", sort_dir: str = "desc"):
    """构建排序键，支持多种排序字段"""
    # rate_multiplier 控制 rate 的排序方向：降序时 negate rate，升序时保持原值
    rate_multiplier = -1 if sort_dir == "desc" else 1

    if sort == "premium_rate":
        pr = item.premium
        if pr and pr.premium_rate is not None:
            rate = pr.premium_rate
            if tab == "arbitrage":
                return (rate * rate_multiplier,)
            # 类别优先级：降序时高溢价在前（category=-3），升序时低溢价在前（category=1）
            # Python sort 是升序，所以 category 越小越靠前
            if rate > HIGH_PREMIUM_THRESHOLD:
                # 降序：高溢价在前 → category=-3；升序：高溢价在后 → category=3
                category = -3 if sort_dir == "desc" else 3
            elif rate > ARBITRAGE_THRESHOLD:
                # 降序：中溢价其次 → category=-2；升序：中溢价其次 → category=2
                category = -2 if sort_dir == "desc" else 2
            else:
                # 降序：低溢价再次 → category=-1；升序：低溢价其次 → category=1
                category = -1 if sort_dir == "desc" else 1
            return (category, rate * rate_multiplier)
        return (0, 0)

    if sort == "estimated_nav":
        pr = item.premium
        if pr and pr.estimated_nav is not None:
            return (pr.estimated_nav * rate_multiplier,)
        return (float('inf') if sort_dir == "desc" else float('-inf'),)

    if sort == "volume":
        vol = item.volume or 0
        return (vol * rate_multiplier,)

    if sort == "daily_limit":
        limit = item.daily_limit or 0
        return (limit * rate_multiplier,)

    if sort == "change_pct":
        change = item.change_pct or 0
        return (change * rate_multiplier,)

    # 默认按溢价率排序
    pr = item.premium
    if pr and pr.premium_rate is not None:
        rate = pr.premium_rate
        if tab == "arbitrage":
            return (-rate * multiplier,)
        if rate > HIGH_PREMIUM_THRESHOLD:
            return (3 * multiplier, -rate * multiplier)
        elif rate > ARBITRAGE_THRESHOLD:
            return (2 * multiplier, -rate * multiplier)
        else:
            return (1 * multiplier, -rate * multiplier)
    return (0, 0)


@router.get("", response_model=FundListResponse)
async def list_funds(
    fund_type: Optional[str] = Query(None, description="基金类型"),
    region: Optional[str] = Query(None, description="跟踪地区"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    sort: str = Query("premium_rate", description="排序字段"),
    sort_dir: Literal["asc", "desc"] = Query("desc", description="排序方向"),
    can_subscribe: Optional[bool] = Query(None, description="是否可申购"),
    premium_level: Optional[str] = Query(None, description="溢价等级: high/normal/discount"),
    arbitrage_type: Optional[str] = Query(None, description="套利类型"),
    tab: Optional[str] = Query(None, description="Tab: all/watchlist/arbitrage/QDII-ETF/QDII-LOF/ETF"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    query = db.query(Fund)
    watched = get_watched_codes(db)

    # Tab 预过滤
    if tab == "watchlist":
        if not watched:
            return FundListResponse(items=[], total=0)
        query = query.filter(Fund.code.in_(watched))
    elif tab == "arbitrage":
        pass  # 套利过滤在内存中进行
    elif tab in ("QDII-ETF", "QDII-LOF", "ETF", "LOF"):
        query = query.filter(Fund.fund_type == tab)
    elif fund_type:
        query = query.filter(Fund.fund_type == fund_type)

    if region:
        query = query.filter(Fund.tracking_region == region)
    if search:
        query = query.filter(
            (Fund.code.like(f"%{search}%")) | (Fund.name.like(f"%{search}%"))
        )

    total = query.count()

    # 套利 tab 或溢价率/估算净值排序：走内存路径
    sql_sort_fields = ("change_pct", "market_price", "volume", "daily_limit")
    force_memory = (tab == "arbitrage" or sort in ("premium_rate", "estimated_nav") or sort not in sql_sort_fields)

    if force_memory:
        all_funds = query.order_by(Fund.code).all()
        items = []
        for fund in all_funds:
            # 套利 tab 额外过滤
            if tab == "arbitrage" and not fund_passes_arbitrage_filter(fund):
                continue
            # 通用筛选
            if not fund_passes_filters(fund, can_subscribe=can_subscribe, premium_level=premium_level, arbitrage_type=arbitrage_type):
                continue
            items.append(build_fund_item(fund, watched, tab=tab))

        items.sort(key=lambda x: build_premium_sort_key(x, tab=tab, sort=sort, sort_dir=sort_dir))

        # 套利 tab 的 total 用内存过滤后的数量
        effective_total = len(items) if tab == "arbitrage" else total

        start = (page - 1) * page_size
        end = start + page_size
        return FundListResponse(items=items[start:end], total=effective_total)

    # SQL 排序路径
    col = getattr(Fund, sort, None)
    if col is not None:
        order_func = col.asc() if sort_dir == "asc" else col.desc()
        funds = query.order_by(order_func).offset((page - 1) * page_size).limit(page_size).all()
    else:
        funds = query.order_by(Fund.code).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for fund in funds:
        if tab == "arbitrage" and not fund_passes_arbitrage_filter(fund):
            continue
        # 通用筛选
        if not fund_passes_filters(fund, can_subscribe=can_subscribe, premium_level=premium_level, arbitrage_type=arbitrage_type):
            continue
        items.append(build_fund_item(fund, watched, tab=tab))

    # 套利 tab 需要遍历全部获取正确 total
    effective_total = total
    if tab == "arbitrage":
        effective_total = sum(1 for f in all_funds if fund_passes_arbitrage_filter(f)) if force_memory else total

    return FundListResponse(items=items, total=effective_total)


@router.get("/tab-counts")
async def get_tab_counts(db: Session = Depends(get_db)):
    watched = get_watched_codes(db)
    all_funds = db.query(Fund).all()
    premiums = get_all_cached_premiums()

    type_counts = {}
    arb_count = 0
    for f in all_funds:
        type_counts[f.fund_type] = type_counts.get(f.fund_type, 0) + 1
        p = premiums.get(f.code, {})
        pr = p.get("premium_rate") or 0
        if (pr > ARBITRAGE_THRESHOLD and f.can_subscribe and f.can_buy is not False and
                (f.daily_limit is None or f.daily_limit >= ARBITRAGE_MIN_DAILY_LIMIT)):
            # 排除 ETF（个人无法参与申赎套利）
            ft = f.fund_type or ''
            if 'ETF' not in ft or 'LOF' in ft:
                arb_count += 1

    return {
        "all": len(all_funds),
        "watchlist": len(watched),
        "arbitrage": arb_count,
        **type_counts,
    }


@router.get("/search")
async def search_funds(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    db: Session = Depends(get_db),
):
    funds = db.query(Fund).filter(
        (Fund.code.like(f"%{q}%")) | (Fund.name.like(f"%{q}%"))
    ).limit(20).all()

    return [
        {"code": f.code, "name": f.name, "fund_type": f.fund_type}
        for f in funds
    ]


@router.get("/{code}", response_model=FundDetail)
async def get_fund_detail(
    code: str,
    db: Session = Depends(get_db),
):
    """获取单只基金详情（含持仓、溢价历史）"""
    fund = db.query(Fund).filter(Fund.code == code).first()
    if not fund:
        return {"code": code, "name": "未知"}

    # 实时计算溢价率
    premium = await calculate_premium(
        fund_code=fund.code,
        fund_name=fund.name,
        nav=fund.nav,
        prev_nav=fund.prev_nav,
        nav_date=str(fund.nav_date) if fund.nav_date else None,
        market_price=fund.market_price,
    )

    # 获取持仓
    holdings = db.query(FundHolding).filter(
        FundHolding.fund_code == code
    ).order_by(FundHolding.holding_date.desc()).limit(10).all()
    holdings_data = [
        {
            "asset_code": h.asset_code,
            "asset_name": h.asset_name,
            "asset_type": h.asset_type,
            "weight": h.weight,
            "market": h.market,
        }
        for h in holdings
    ]

    # 获取溢价历史（最近30天）
    snapshots = db.query(PremiumSnapshot).filter(
        PremiumSnapshot.fund_code == code
    ).order_by(PremiumSnapshot.snapshot_time.desc()).limit(200).all()
    history_data = [
        {
            "time": str(s.snapshot_time),
            "premium_rate": s.premium_rate,
            "market_price": s.market_price,
            "nav_value": s.nav_value,
            "calc_method": s.calc_method,
        }
        for s in snapshots
    ]

    # 构建 premium 对象
    premium_obj = None
    if premium and premium.get("method"):
        premium_copy = {**premium}
        premium_copy["calc_method"] = premium_copy.pop("method")
        premium_obj = FundPremium(**premium_copy)

    return FundDetail(
        code=fund.code,
        name=fund.name,
        fund_type=fund.fund_type,
        manager=fund.manager,
        underlying_index=fund.underlying_index,
        tracking_region=fund.tracking_region,
        exchange=fund.exchange,
        trading_venue=fund.trading_venue,
        can_subscribe=fund.can_subscribe,
        subscribe_status=fund.subscribe_status,
        daily_limit=fund.daily_limit,
        can_buy=fund.can_buy,
        can_sell=fund.can_sell,
        nav_date=fund.nav_date,
        nav=fund.nav,
        prev_nav=fund.prev_nav,
        nav_accuracy=fund.nav_accuracy,
        market_price=fund.market_price,
        prev_close=fund.prev_close,
        change_pct=fund.change_pct,
        premium=premium_obj,
        holdings=holdings_data,
        premium_history=history_data,
    )
