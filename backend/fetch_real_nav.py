"""fetch_real_nav.py：通过天天基金 API 获取所有 QDII 基金净值并注入数据库"""
import sys, os, json, re, httpx
sys.path.insert(0, os.path.dirname(__file__))

from datetime import date
from database import SessionLocal
from models import Fund
from services.premium_service import cache_premium

# NAV accuracy 映射：跟踪区域 → 净值延迟
REGION_NAV_ACCURACY = {
    "HK": "T-1",
    "US": "T-2", "JP": "T-2", "EU": "T-2", "IN": "T-2", "SA": "T-2", "BR": "T-2",
    "HK+US": "T-2", "CN+KR": "T-2", "HK+IN+TW": "T-2", "IN+KR+TW": "T-2",
    "HK+JP+AU": "T-2",
}

# 手动修正净值：用于数据源无法获取的基金
# 格式: {基金代码: {'nav': 净值, 'nav_date': '日期', 'source': '来源说明'}}
MANUAL_NAV_CORRECTIONS = {
    # 501225 全球芯片 LOF - 天天基金/东方财富均无数据，根据集思录数据手动修正
    # 2026-05-27: 用户反馈溢价 40%+，现价 3.938，反推净值约 2.81
    "501225": {
        "nav": 2.81,
        "nav_date": "2026-05-25",
        "source": "manual_correction",
        "note": "天天基金/东方财富无数据，根据用户反馈溢价率反推"
    },
}

def get_nav_accuracy(fund):
    """根据基金跟踪区域确定净值延迟"""
    if fund and fund.tracking_region and fund.tracking_region in REGION_NAV_ACCURACY:
        return REGION_NAV_ACCURACY[fund.tracking_region]
    return "T-2"  # QDII 默认 T-2


# 从数据库获取所有 QDII 基金代码
db = SessionLocal()
try:
    FUND_CODES = [f.code for f in db.query(Fund.code).filter(
        Fund.fund_type.in_(["QDII-ETF", "QDII-LOF"])
    ).all()]
    print(f'数据库中共有 {len(FUND_CODES)} 只 QDII 基金\n')
finally:
    db.close()

results = {}
with httpx.Client(timeout=10) as client:
    for code in FUND_CODES:
        try:
            r = client.get(f'http://fundgz.1234567.com.cn/js/{code}.js')
            match = re.search(r'jsonpgz\((.*?)\);', r.text)
            if match:
                d = json.loads(match.group(1))
                nav = float(d.get('dwjz', 0))
                est = float(d.get('gsz', 0))
                change = float(d.get('gszzl', 0))
                gztime = d.get('gztime', '')
                name = d.get('name', '')
                if nav > 0:
                    results[code] = {
                        'nav': nav,
                        'estimated_nav': est,
                        'change_pct': change,
                        'nav_date': gztime[:10],
                        'name': name,
                    }
                    print(f'  OK  {code}  {name:25s}  NAV={nav}  Est={est}  Change={change:+.2f}%')
                else:
                    print(f'  SKIP {code}  净值无效')
            else:
                print(f'  --   {code}  无数据，待历史API补充')
        except Exception as e:
            print(f'  ERR  {code}  {str(e)[:50]}')

# 对没有数据的，尝试历史净值 API
missing_codes = [c for c in FUND_CODES if c not in results]
if missing_codes:
    print(f'\n正在获取 {len(missing_codes)} 只缺失基金的历史净值...')
    with httpx.Client(timeout=15) as client:
        for code in missing_codes:
            try:
                r = client.get(
                    'https://fundf10.eastmoney.com/F10DataApi.aspx',
                    params={
                        'type': 'lsjz',
                        'code': code,
                        'page': '1',
                        'size': '1',
                    },
                    headers={'User-Agent': 'Mozilla/5.0'},
                )
                text = r.text.strip()
                match_date = re.search(r'净值日期.*?<td[^>]*>(\d{4}-\d{2}-\d{2})</td>', text, re.DOTALL)
                match_nav = re.search(r'单位净值.*?<td[^>]*>([\d.]+)</td>', text, re.DOTALL)
                if match_date and match_nav:
                    nav = float(match_nav.group(1))
                    nav_date = match_date.group(1)
                    results[code] = {
                        'nav': nav,
                        'estimated_nav': nav,
                        'change_pct': 0,
                        'nav_date': nav_date,
                        'name': code,
                    }
                    print(f'  OK  {code}  NAV={nav}  Date={nav_date}')
                else:
                    print(f'  --   {code}  历史净值解析失败，保留原有净值')
            except Exception as e:
                print(f'  ERR  {code}  {str(e)[:50]}')

print(f'\n成功获取 {len(results)}/{len(FUND_CODES)} 只基金净值')

# 应用手动修正的净值
for code, correction in MANUAL_NAV_CORRECTIONS.items():
    if code not in results:
        print(f'  [手动修正] {code} 净值={correction["nav"]} ({correction["note"]})')
        results[code] = {
            'nav': correction['nav'],
            'estimated_nav': correction['nav'],
            'change_pct': 0,
            'nav_date': correction['nav_date'],
            'name': code,
            'source': 'manual_correction',
        }

print(f'应用手动修正后: {len(results)}/{len(FUND_CODES)} 只基金净值')

# 写入数据库
db = SessionLocal()
try:
    updated = 0
    for code, data in results.items():
        fund = db.query(Fund).filter(Fund.code == code).first()
        if fund:
            fund.nav = data['nav']
            # 不修改 market_price - 市场价格由实时行情更新
            fund.prev_close = round(data['nav'] / (1 + data['change_pct'] / 100), 4) if data['change_pct'] != 0 else data['nav']
            fund.change_pct = data['change_pct']
            try:
                fund.nav_date = date.fromisoformat(data['nav_date'])
            except:
                pass

            # 根据跟踪区域设置 NAV accuracy
            fund.nav_accuracy = get_nav_accuracy(fund)

            cache_premium(code, {
                "method": "C",
                "estimated_nav": data['nav'],
                "nav_type": fund.nav_accuracy,
                "premium_rate": 0.0,
            })
            updated += 1

    db.commit()
    print(f'已更新 {updated} 只基金到数据库')
finally:
    db.close()
