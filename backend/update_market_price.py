"""update_market_price.py：批量更新所有QDII基金实时价格和溢价率
使用东方财富批量行情API获取真实场内交易价格
"""
import sys, os, json, httpx
import time

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

def get_secid(code: str) -> str:
    """基金代码转secid"""
    if code.startswith("15"):
        return f"0.{code}"  # 深交所
    elif code.startswith(("5", "6", "50", "51", "52")):
        return f"1.{code}"  # 上交所
    elif code.startswith(("16", "1", "2", "3", "4")):
        return f"0.{code}"  # 深交所LOF
    else:
        return f"1.{code}"

def get_batch_quotes(secids: list) -> dict:
    """批量获取行情 - 东方财富API"""
    url = "https://push2.eastmoney.com/api/qt/ulist.np/get"
    # f2=最新价, f3=涨跌幅%, f4=涨跌额, f57=代码, f58=名称, f60=昨收, f61=今开, f5=最高, f6=最低
    params = {
        "secids": ",".join(secids),
        "fields": "f2,f3,f4,f57,f58,f60,f61,f5,f6",
        "fltt": "2",
        "ut": "fa5fd1943c7b386f172d6893dbfba10b",
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://quote.eastmoney.com/center/gridlist.html#fund_etf",
        "Accept": "application/json",
    }
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(url, params=params, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                quotes = {}
                for item in data.get("data", {}).get("diff", []):
                    code = item.get("f57", "")
                    quotes[code] = {
                        "price": float(item.get("f2", 0)),
                        "change_pct": float(item.get("f3", 0)),
                        "change_amt": float(item.get("f4", 0)),
                        "prev_close": float(item.get("f60", 0)),
                        "open": float(item.get("f61", 0)),
                        "high": float(item.get("f5", 0)),
                        "low": float(item.get("f6", 0)),
                    }
                return quotes
    except Exception as e:
        print(f"  API error: {e}")
    return {}

# 主流程
db = SessionLocal()
funds = db.query(Fund).filter(Fund.fund_type.in_(["QDII-ETF", "QDII-LOF"])).all()
db.close()

fund_codes = [f.code for f in funds]
print(f"共 {len(fund_codes)} 只 QDII 基金，批量更新实时价格...\n")

# 分批处理（每批80只，留余量）
BATCH_SIZE = 80
total_updated = 0
total_failed = 0

for i in range(0, len(fund_codes), BATCH_SIZE):
    batch_codes = fund_codes[i:i+BATCH_SIZE]
    secids = [get_secid(c) for c in batch_codes]
    batch_num = i // BATCH_SIZE + 1
    print(f"批次 {batch_num}: 查询 {len(batch_codes)} 只基金...")

    quotes = get_batch_quotes(secids)

    db = SessionLocal()
    batch_ok = 0
    for code in batch_codes:
        fund = db.query(Fund).filter(Fund.code == code).first()
        if not fund:
            continue

        quote = quotes.get(code)
        if quote and quote["price"] > 0:
            old_price = fund.market_price
            fund.market_price = quote["price"]
            fund.change_pct = quote["change_pct"]
            fund.prev_close = quote["prev_close"] if quote["prev_close"] > 0 else fund.prev_close

            # 重新计算溢价率
            premium = 0
            if fund.nav and fund.nav > 0:
                premium = (fund.market_price - fund.nav) / fund.nav * 100

            cache_premium(code, {
                "method": "C",
                "estimated_nav": fund.nav,
                "nav_type": get_nav_accuracy(fund.tracking_region),
                "premium_rate": premium,
            })

            if old_price != fund.market_price:
                total_updated += 1
                diff = abs(fund.market_price - old_price) / old_price * 100 if old_price and old_price > 0 else 0
                if diff > 1.0:
                    print(f"  UPDATE {code} {old_price:.4f} -> {fund.market_price:.4f} 溢价={premium:+.2f}%")
            batch_ok += 1
        else:
            total_failed += 1

    db.commit()
    db.close()
    print(f"  批次完成: {batch_ok} 只成功")

print(f"\n{'='*60}")
print(f"更新完成: 价格变动 {total_updated} 只, 无数据 {total_failed} 只")
print(f"{'='*60}")
