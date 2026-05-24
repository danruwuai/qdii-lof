"""FastAPI 入口"""
import sys
import os
import asyncio

# 加载 .env 文件
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Windows + Git Bash 兼容：设置事件循环策略以支持 Playwright 子进程
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

sys.path.insert(0, os.path.dirname(__file__))

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from api import funds, watchlist, alerts, realtime, wechat
from services.scheduler import setup_scheduler
from services.market_hours import get_all_active_markets
from schemas import MarketStatus


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化
    init_db()
    load_mock_cache()
    scheduler = setup_scheduler()
    scheduler.start()
    app.state.scheduler = scheduler
    
    # 启动后立即计算一次溢价率（填充缓存）
    from services.scheduler import compute_all_premiums
    await compute_all_premiums()
    
    yield
    # 关闭时清理
    scheduler.shutdown()


def load_mock_cache():
    """加载模拟缓存数据（用于预览，实际运行时由调度器刷新）"""
    from services.premium_service import cache_premium
    from models import Fund
    from database import SessionLocal

    db = SessionLocal()
    try:
        # 从 PremiumSnapshot 读取最近数据恢复缓存
        from models import PremiumSnapshot
        from sqlalchemy import func
        subq = db.query(
            PremiumSnapshot.fund_code,
            func.max(PremiumSnapshot.snapshot_time).label("max_time")
        ).group_by(PremiumSnapshot.fund_code).subquery()

        latest = db.query(PremiumSnapshot).join(
            subq,
            (PremiumSnapshot.fund_code == subq.c.fund_code) &
            (PremiumSnapshot.snapshot_time == subq.c.max_time)
        ).all()

        for snap in latest:
            nav_val = snap.nav_value or 0
            rate = snap.premium_rate or 0
            estimated = round(nav_val / (1 + rate / 100), 4) if rate != 0 else nav_val
            cache_premium(snap.fund_code, {
                "method": snap.calc_method,
                "estimated_nav": estimated,
                "nav_type": snap.nav_type,
                "premium_rate": rate,
            })
        print(f"Restored {len(latest)} premium cache entries from snapshots")
    finally:
        db.close()


app = FastAPI(title="QDII LOF ETF 溢价率监控", version="0.1.0", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(funds.router)
app.include_router(watchlist.router)
app.include_router(alerts.router)
app.include_router(realtime.router)
app.include_router(wechat.router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/v1/market-status", response_model=MarketStatus)
async def market_status():
    from datetime import datetime
    active = get_all_active_markets()
    return MarketStatus(
        cn="open" if "CN" in active else "closed",
        hk="open" if "HK" in active else "closed",
        us="open" if "US" in active else "closed",
        jp="open" if "JP" in active else "closed",
        eu="open" if "EU" in active else "closed",
        timestamp=datetime.now().isoformat(),
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
