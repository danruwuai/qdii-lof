"""fix_all_nav.py：并发批量更新所有QDII基金净值（东方财富API）"""
import sys, os, re, json, httpx
from datetime import date
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(__file__))
from database import SessionLocal
from models import Fund
from services.premium_service import cache_premium

REGION_NAV_ACCURACY = {
    "HK": "T-1", "US": "T-2", "JP": "T-2", "EU": "T-2", "IN": "T-2", "SA": "T-2", "BR": "T-2",
    "HK+US": "T-2", "CN+KR": "T-2", "HK+IN+TW": "T-2", "IN+KR+TW": "T-2", "HK+JP+AU": "T-2",
}

def get_nav_accuracy(tracking_region):
    if tracking_region and tracking_region in REGION_NAV_ACCURACY:
        return REGION_NAV_ACCURACY[tracking_region]
    return "T-2"

def fetch_nav(fund_code: str) -> dict | None:
    """并发安全的净值获取"""
    # 1. 东方财富API
    url = "http://api.fund.eastmoney.com/f10/lsjz"
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(url, params={"fundCode": fund_code, "pageIndex": "1", "pageSize": "2"})
            if resp.status_code == 200:
                data = resp.json()
                lsjz = data.get("Data", {}).get("LSJZList", [])
                if lsjz and lsjz[0].get("DWJZ") and lsjz[0].get("DWJZ") != "--":
                    return {
                        "nav": float(lsjz[0]["DWJZ"]),
                        "nav_date": lsjz[0].get("FSRQ", ""),
                        "source": "eastmoney",
                    }
    except Exception:
        pass

    # 2. 天天基金fallback
    try:
        with httpx.Client(timeout=5) as client:
            resp = client.get(f"http://fundgz.1234567.com.cn/js/{fund_code}.js")
            match = re.search(r"jsonpgz\((\{.*?\})\)", resp.text)
            if match:
                data = json.loads(match.group(1))
                dwjz = data.get("dwjz")
                if dwjz and float(dwjz) > 0:
                    return {
                        "nav": float(dwjz),
                        "nav_date": data.get("jzrq", ""),
                        "source": "tiantian",
                    }
    except Exception:
        pass

    return None

def update_fund(fund):
    """更新单只基金"""
    code = fund.code
    nav_data = fetch_nav(code)

    if not nav_data:
        return (code, fund.name, "FAIL", None)

    fund.nav = nav_data["nav"]
    try:
        fund.nav_date = date.fromisoformat(nav_data["nav_date"])
    except:
        pass
    fund.nav_accuracy = get_nav_accuracy(fund.tracking_region)

    premium = 0
    if fund.market_price and fund.market_price > 0:
        premium = (fund.market_price - fund.nav) / fund.nav * 100

    cache_premium(code, {
        "method": "C",
        "estimated_nav": fund.nav,
        "nav_type": fund.nav_accuracy,
        "premium_rate": premium,
    })

    return (code, fund.name, "OK", nav_data, premium)

# 主流程
db = SessionLocal()
funds = db.query(Fund).filter(Fund.fund_type.in_(["QDII-ETF", "QDII-LOF"])).all()
print(f"共 {len(funds)} 只 QDII 基金，并发更新中...\n")

results = {}
with ThreadPoolExecutor(max_workers=20) as executor:
    futures = {executor.submit(update_fund, f): f for f in funds}
    completed = 0
    for future in as_completed(futures):
        code, name, status, nav_data, premium = future.result()
        results[code] = (status, nav_data, premium)
        completed += 1

        if status == "OK":
            print(f"  [{completed:3d}/{len(funds)}] OK   {code} {name[:25]:<25} NAV={nav_data['nav']:<10} Date={nav_data['nav_date']} 溢价={premium:+.2f}%  [{nav_data['source']}]")
        else:
            print(f"  [{completed:3d}/{len(funds)}] FAIL {code} {name[:25]:<25} 无数据")

db.commit()
db.close()

# 统计
ok_count = sum(1 for v in results.values() if v[0] == "OK")
fail_count = len(results) - ok_count
print(f"\n{'='*70}")
print(f"更新完成: 成功 {ok_count} 只, 失败 {fail_count} 只")
print(f"{'='*70}")

if fail_count > 0:
    print(f"\n失败的基金:")
    for code, (status, _, _) in results.items():
        if status == "FAIL":
            print(f"  {code}")
