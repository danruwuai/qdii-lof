"""mock_data.py：注入模拟行情和溢价数据，用于预览效果"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import date
from database import SessionLocal, init_db
from models import Fund, PremiumSnapshot
from services.premium_service import cache_premium

# 模拟行情数据
MOCK_DATA = [
    # code, price, change, nav, nav_date, premium_rate, calc_method
    ("513500", 1.523, 1.25, 1.510, "2026-05-14", 0.86, "A"),
    ("513100", 1.892, 2.10, 1.853, "2026-05-14", 2.10, "A"),
    ("159941", 1.456, -0.82, 1.445, "2026-05-14", 0.76, "A"),
    ("513630", 1.328, 0.45, 1.320, "2026-05-14", 0.61, "A"),
    ("513030", 1.105, -0.36, 1.100, "2026-05-14", 0.45, "A"),
    ("513880", 1.268, 0.94, 1.255, "2026-05-13", 1.04, "A"),
    ("513800", 1.271, 0.87, 1.258, "2026-05-13", 1.03, "A"),
    ("518880", 5.823, 0.34, 5.805, "2026-05-16", 0.31, "C"),
    ("159513", 1.045, 1.56, 1.028, "2026-05-14", 1.65, "A"),
    ("159300", 1.042, 1.48, 1.026, "2026-05-14", 1.56, "A"),
    ("513660", 0.782, -1.26, 0.778, "2026-05-16", 0.51, "C"),
    ("513690", 0.695, -0.86, 0.690, "2026-05-16", 0.72, "C"),
    ("513600", 0.658, -1.94, 0.648, "2026-05-16", 1.54, "A"),
    ("159740", 0.655, -2.10, 0.645, "2026-05-16", 1.55, "A"),
    ("164906", 1.185, 3.21, 1.142, "2026-05-14", 3.77, "A"),
    ("513050", 1.098, 2.85, 1.068, "2026-05-14", 2.81, "A"),
    ("513750", 0.986, 2.92, 0.958, "2026-05-14", 2.92, "A"),
    ("161129", 1.632, 1.12, 1.628, "2026-05-14", 0.25, "C"),
    ("161716", 1.156, 0.09, 1.155, "2026-05-16", 0.09, "C"),
    ("160137", 1.892, 0.58, 1.885, "2026-05-16", 0.37, "C"),
    ("510300", 3.958, 0.76, 3.955, "2026-05-16", 0.08, "C"),
    ("510500", 6.125, 1.05, 6.120, "2026-05-16", 0.08, "C"),
    ("159919", 4.326, 0.72, 4.323, "2026-05-16", 0.07, "C"),
    ("588000", 0.925, 1.87, 0.923, "2026-05-16", 0.22, "C"),
    ("512100", 0.895, 1.36, 0.893, "2026-05-16", 0.22, "C"),
    ("159995", 1.432, 2.36, 1.428, "2026-05-16", 0.28, "C"),
    ("512480", 0.823, 1.98, 0.820, "2026-05-16", 0.37, "C"),
    ("515050", 0.756, 2.72, 0.752, "2026-05-16", 0.53, "C"),
    ("512660", 0.918, -0.54, 0.915, "2026-05-16", 0.33, "C"),
    ("515790", 0.682, 0.89, 0.680, "2026-05-16", 0.29, "C"),
]


def seed_mock_data():
    db = SessionLocal()
    try:
        for code, price, change, nav, nav_date, premium, method in MOCK_DATA:
            fund = db.query(Fund).filter(Fund.code == code).first()
            if fund:
                fund.market_price = price
                fund.prev_close = round(price / (1 + change / 100), 3)
                fund.change_pct = change
                fund.nav = nav
                fund.nav_date = date.fromisoformat(nav_date)
                fund.nav_accuracy = "T-1" if fund.tracking_region != "CN" else "T-1"
                fund.volume = round(price * 1000000, 0)
                fund.turnover = round(price * 50000000, 0)
                fund.float_cap = round(price * 1e9, 0)

                # 申购状态（模拟）
                if code in ("164906", "513050", "513750"):
                    fund.subscribe_status = "限额"
                    fund.can_subscribe = True
                    fund.daily_limit = 10000  # 1万限额
                elif code in ("159300", "159513"):
                    fund.subscribe_status = "暂停"
                    fund.can_subscribe = False
                    fund.daily_limit = None
                else:
                    fund.subscribe_status = "开放"
                    fund.can_subscribe = True
                    fund.daily_limit = None

                # 缓存溢价率
                cache_premium(code, {
                    "method": method,
                    "estimated_nav": round(nav * (1 + premium / 100), 4),
                    "nav_type": "estimated" if method == "A" else "confirmed_T1",
                    "premium_rate": premium,
                })

                # 写快照
                snapshot = PremiumSnapshot(
                    fund_code=code,
                    market_price=price,
                    nav_value=round(nav * (1 + premium / 100), 4),
                    nav_type="estimated" if method == "A" else "confirmed_T1",
                    premium_rate=premium,
                    calc_method=method,
                )
                db.add(snapshot)

        db.commit()
        print(f"Injected mock data for {len(MOCK_DATA)} funds")
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
    seed_mock_data()
    print("Done! Restart the server and check the API.")
