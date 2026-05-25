"""APScheduler 定时任务调度器"""
import asyncio
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session

from database import SessionLocal
from models import Fund, PremiumSnapshot
from data_sources import akshare_source
from data_sources import eastmoney_source
from data_sources import fetch_qdii_list, fetch_lof_list  # 双源 fallback
from data_sources.nav_source import get_fund_nav_multi_source
from services.nav_calculator import calculate_premium
from services.premium_service import cache_premium
from services.market_hours import get_all_active_markets
from services.alert_engine import check_all_alerts
from api.realtime import broadcast_premium_update
import config

# 线程池用于运行同步阻塞任务
executor = ThreadPoolExecutor(max_workers=4)

scheduler = AsyncIOScheduler()


def _safe_float(val):
    """安全转浮点数"""
    if val is None or val == "--" or val == "-" or val == "":
        return None
    try:
        return float(str(val).replace("%", ""))
    except (ValueError, TypeError):
        return None


async def refresh_cn_quotes():
    """刷新 A 股 ETF/LOF 实时行情（使用集思录的实时价格，HTTP 优先 + Playwright 降级）"""
    try:
        qdii_data = await fetch_qdii_list(config.JISILI_COOKIE)
        lof_data = await fetch_lof_list(config.JISILI_COOKIE)
    except Exception as e:
        print(f"[行情刷新] 集思录获取失败: {e}")
        return

    all_data = qdii_data + lof_data
    if not all_data:
        return

    db = SessionLocal()
    try:
        updated_price = 0
        updated_nav = 0
        updated_chg = 0
        for item in all_data:
            code = item.get("fund_code")
            price = item.get("price")
            nav = item.get("fund_nav")
            nav_date = item.get("nav_date") or item.get("nav_dt_s", "")
            if not code:
                continue
            fund = db.query(Fund).filter(Fund.code == code).first()
            if not fund:
                continue

            # 更新实时价格
            if price:
                fund.market_price = price
                fund.volume = item.get("volume")
                updated_price += 1

                # 计算 change_pct（当日涨跌幅）
                # 优先用指数涨跌幅（适用于指数基金/QDII）
                index_chg = _safe_float(item.get("index_increase_rt"))
                if index_chg is not None:
                    fund.change_pct = index_chg
                    fund.prev_close = round(price / (1 + index_chg / 100), 4)
                    updated_chg += 1
                # LOF 非指数基金：用 (price - 最新净值) / 最新净值 作为近似
                # 注意：这实际上是溢价率，不是涨跌幅，但 LOF 没有更好数据源
                elif fund.nav:
                    fund.change_pct = round((price - fund.nav) / fund.nav * 100, 2)
                    fund.prev_close = round(fund.nav, 4)
                    updated_chg += 1

            # 更新净值（集思录净值比多数据源更全，作为补充）
            nav_val = _safe_float(nav)
            if nav_val:
                fund.nav = nav_val
                if nav_date:
                    try:
                        fund.nav_date = datetime.strptime(nav_date, "%Y-%m-%d").date()
                    except ValueError:
                        pass
                updated_nav += 1

            fund.updated_at = datetime.now()
        db.commit()
        print(f"[行情刷新] 更新了 {updated_price} 只价格, {updated_nav} 只净值, {updated_chg} 只涨跌幅")
    finally:
        db.close()


async def refresh_fund_nav():
    """刷新基金净值（每日）- 使用多数据源 fallback"""
    db = SessionLocal()
    try:
        funds = db.query(Fund).all()
        updated_count = 0
        for fund in funds:
            # 使用多数据源获取净值
            nav_info = await get_fund_nav_multi_source(fund.code)
            if nav_info and nav_info.get("nav"):
                fund.nav = nav_info["nav"]
                fund.prev_nav = nav_info.get("prev_nav")
                if nav_info.get("nav_date"):
                    try:
                        fund.nav_date = datetime.strptime(nav_info["nav_date"], "%Y-%m-%d").date()
                    except ValueError:
                        pass
                fund.nav_accuracy = nav_info.get("nav_accuracy", "estimated")
                fund.updated_at = datetime.now()
                updated_count += 1
                if "mapped_from" in nav_info:
                    print(f"  [映射] {fund.code} → {nav_info['actual_code']} ({nav_info['source']})")
            else:
                print(f"  [跳过] {fund.code} {fund.name} - 无净值数据")

        db.commit()
        print(f"净值刷新完成: {updated_count}/{len(funds)} 只基金更新成功")
    finally:
        db.close()


async def refresh_subscription_status():
    """刷新申购状态（从集思录，HTTP 优先 + Playwright 降级）"""
    qdii_data = await fetch_qdii_list(config.JISILI_COOKIE)
    lof_data = await fetch_lof_list(config.JISILI_COOKIE)

    all_data = qdii_data + lof_data
    if not all_data:
        return

    db = SessionLocal()
    try:
        for item in all_data:
            fund = db.query(Fund).filter(Fund.code == item["fund_code"]).first()
            if fund:
                fund.subscribe_status = item.get("fund_status", "")
                fund.can_subscribe = item.get("enable_gr") == "Y"
                # 解析限额
                limit_str = item.get("limit_amount", "")
                if limit_str and limit_str != "--" and limit_str != "无限":
                    try:
                        fund.daily_limit = float(str(limit_str).replace("万", "0000"))
                    except (ValueError, TypeError):
                        pass
                else:
                    fund.daily_limit = None
        db.commit()
    finally:
        db.close()


async def compute_all_premiums():
    """计算所有有完整数据的基金溢价率"""
    active_markets = get_all_active_markets()

    db = SessionLocal()
    try:
        funds = db.query(Fund).filter(
            Fund.market_price != None,
            Fund.nav != None,
        ).all()
        print(f"  溢价计算: {len(funds)} 只 (活跃市场: {active_markets})")

        if not funds:
            print("  无基金需要计算")
            return

        for fund in funds:
            if not fund.market_price or not fund.nav:
                continue

            # 用 Type C 兜底（T-1 净值），避免 Type A 的网络请求
            # Type A 需要实时指数行情，太重了
            use_nav = fund.prev_nav or fund.nav
            premium = await calculate_premium(
                fund_code=fund.code,
                fund_name=fund.name,
                nav=fund.nav,
                prev_nav=fund.prev_nav,
                nav_date=str(fund.nav_date) if fund.nav_date else None,
                market_price=fund.market_price,
            )

            if premium.get("method"):
                cache_premium(fund.code, premium)

                # 保存到快照
                snapshot = PremiumSnapshot(
                    fund_code=fund.code,
                    market_price=fund.market_price,
                    nav_value=premium.get("estimated_nav"),
                    nav_type=premium.get("nav_type"),
                    premium_rate=premium.get("premium_rate"),
                    calc_method=premium.get("method"),
                )
                db.add(snapshot)

                # WebSocket 推送（包含 market_price，小程序需要）
                premium_data = {**premium, "market_price": fund.market_price}
                if "method" in premium_data:
                    premium_data["calc_method"] = premium_data.pop("method")
                await broadcast_premium_update(fund.code, premium_data)

        db.commit()
    finally:
        db.close()


async def refresh_holdings():
    """刷新基金持仓（每周）"""
    db = SessionLocal()
    try:
        from models import FundHolding
        funds = db.query(Fund).all()
        for fund in funds:
            holdings = akshare_source.get_fund_holdings(fund.code, "2024")
            for h in holdings:
                existing = db.query(FundHolding).filter(
                    FundHolding.fund_code == fund.code,
                    FundHolding.asset_code == h["asset_code"],
                ).first()
                if existing:
                    existing.weight = h.get("weight")
                else:
                    db.add(FundHolding(
                        fund_code=fund.code,
                        asset_code=h["asset_code"],
                        asset_name=h["asset_name"],
                        weight=h.get("weight"),
                        asset_type="stock",
                    ))
        db.commit()
    finally:
        db.close()


def setup_scheduler():
    """配置所有定时任务"""
    # 实时行情（集思录）：每 5 分钟
    scheduler.add_job(refresh_cn_quotes, "interval", seconds=300, max_instances=1)

    # 基金净值：每日 20:00
    scheduler.add_job(refresh_fund_nav, "cron", hour=20, minute=0, day_of_week="mon-fri")

    # 申购状态：每 10 分钟
    scheduler.add_job(refresh_subscription_status, "cron", hour="9-18", minute="*/10", day_of_week="mon-fri")

    # 持仓：每周日 02:00
    scheduler.add_job(refresh_holdings, "cron", hour=2, minute=0, day_of_week="sun")

    # 溢价率计算 + 推送：每 10 秒
    scheduler.add_job(compute_all_premiums, "interval", seconds=config.REFRESH_INTERVAL_PREMIUM, max_instances=1)

    # 提醒检测：每 30 秒
    scheduler.add_job(check_all_alerts, "interval", seconds=30, max_instances=1)

    return scheduler
