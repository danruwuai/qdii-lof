"""seed.py：初始数据填充（QDII / 跨境 LOF 种子数据）"""
import sys
import os
import asyncio
sys.path.insert(0, os.path.dirname(__file__))

from database import engine, SessionLocal, init_db
from models import Fund
from utils.index_mapper import INDEX_MAPPING, get_index_mapping


def seed_funds_from_jisilu(qdii_data: list[dict], lof_data: list[dict]):
    """从集思录数据批量导入基金"""
    db = SessionLocal()
    try:
        existing = {f.code for f in db.query(Fund.code).all()}
        added = 0
        updated = 0

        for item in qdii_data + lof_data:
            code = item["fund_code"]
            name = item.get("name", "")
            qtype = item.get("qtype", "")
            lof_type = item.get("lof_type", "")

            # 判断基金类型
            fund_type = "QDII-ETF" if qtype in ("E", "A", "C") else "QDII-LOF"

            # 判断交易所
            exchange = "SH" if code.startswith(("5", "6")) else "SZ"

            # 尝试获取指数映射
            mapping = get_index_mapping(code, name)

            fund = db.query(Fund).filter(Fund.code == code).first()
            if fund:
                # 更新已有基金
                if not fund.name or fund.name != name:
                    fund.name = name
                    updated += 1
                if not fund.fund_type:
                    fund.fund_type = fund_type
                if mapping:
                    fund.underlying_index = mapping.get("index_name")
                    fund.underlying_index_code = mapping.get("index_code")
                    fund.tracking_region = mapping.get("region")
                    fund.position_ratio = mapping.get("position_ratio", 0.95)
            else:
                # 新建基金
                fund_kwargs = {
                    "code": code,
                    "name": name,
                    "fund_type": fund_type,
                    "exchange": exchange,
                    "trading_venue": "场内",
                }
                if mapping:
                    fund_kwargs.update({
                        "underlying_index": mapping.get("index_name"),
                        "underlying_index_code": mapping.get("index_code"),
                        "tracking_region": mapping.get("region"),
                        "position_ratio": mapping.get("position_ratio", 0.95),
                    })
                fund = Fund(**fund_kwargs)
                db.add(fund)
                added += 1

        db.commit()
        print(f"集思录导入: 新增 {added} 只, 更新 {updated} 只")
    finally:
        db.close()


def seed_index_mappings():
    """更新已知基金的指数映射和区域信息"""
    db = SessionLocal()
    try:
        for code, mapping in INDEX_MAPPING.items():
            fund = db.query(Fund).filter(Fund.code == code).first()
            if fund:
                fund.underlying_index = mapping.get("index_name")
                fund.underlying_index_code = mapping.get("index_code")
                fund.tracking_region = mapping.get("region")
                fund.position_ratio = mapping.get("position_ratio", 0.95)
            else:
                fund = Fund(
                    code=code,
                    name=mapping.get("index_name", code),
                    fund_type="QDII-ETF",
                    underlying_index=mapping.get("index_name"),
                    underlying_index_code=mapping.get("index_code"),
                    tracking_region=mapping.get("region"),
                    position_ratio=mapping.get("position_ratio", 0.95),
                )
                db.add(fund)
        db.commit()
        print(f"Seeded {len(INDEX_MAPPING)} index mappings")
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
    print("Initializing database...")

    # 从集思录导入
    from dotenv import load_dotenv
    load_dotenv()
    import config
    from data_sources import jisilu_source

    async def fetch_and_seed():
        qdii_data = await jisilu_source.fetch_qdii_list(config.JISILI_COOKIE)
        lof_data = await jisilu_source.fetch_lof_list(config.JISILI_COOKIE)
        seed_funds_from_jisilu(qdii_data, lof_data)
        seed_index_mappings()
        print("Done!")

    asyncio.run(fetch_and_seed())
