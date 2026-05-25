"""
迁移脚本：SQLite → Cloudflare D1

用法：
  python migrate_to_d1.py --export [--days 7]   # 导出为 SQL（可指定保留天数）
  python migrate_to_d1.py --json [--days 7]     # 导出为 JSON
  python migrate_to_d1.py --schema              # 打印 schema
"""

import sqlite3
import json
import os
import sys
from datetime import datetime, timedelta

def get_db_path():
    return os.path.join(os.path.dirname(__file__), 'data', 'qdii_v2.db')


def get_db_schema():
    """获取当前 SQLite 数据库的完整 schema"""
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()

    cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL")
    tables = cursor.fetchall()

    schema_sql = []
    for name, sql in tables:
        if name.startswith('sqlite_'):
            continue
        schema_sql.append(f"-- Table: {name}")
        schema_sql.append(sql + ';')
        schema_sql.append('')

    conn.close()
    return '\n'.join(schema_sql)


def export_data_to_sql(days: int = 7, all_data: bool = False):
    """导出所有数据为 INSERT 语句（premium_snapshots 只保留最近 N 天）"""
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()

    output = []
    output.append("-- QDII LOF ETF 数据库迁移脚本")
    output.append(f"-- 生成时间: {datetime.now().isoformat()}")
    output.append(f"-- premium_snapshots 保留最近 {days} 天")
    output.append("")

    # 导出 schema
    output.append("-- ===== Schema =====")
    output.append(get_db_schema())

    # 导出每张表的数据
    tables_to_export = ['funds', 'fund_holdings', 'user_watchlist', 'user_alerts']

    for table in tables_to_export:
        cursor.execute(f"SELECT * FROM {table}")
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()

        if not rows:
            continue

        output.append(f"-- {table}: {len(rows)} rows")

        for row in rows:
            values = []
            for val in row:
                if val is None:
                    values.append('NULL')
                elif isinstance(val, (int, float)):
                    values.append(str(val))
                elif isinstance(val, datetime):
                    values.append(f"'{val.isoformat()}'")
                else:
                    escaped = str(val).replace("'", "''")
                    values.append(f"'{escaped}'")

            output.append(f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(values)});")

        output.append('')

    # premium_snapshots - 只保留最近 N 天（或用 --all 导出全部）
    if all_data:
        cursor.execute("SELECT * FROM premium_snapshots")
    else:
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(
            f"SELECT * FROM premium_snapshots WHERE snapshot_time >= '{cutoff_date}'"
        )
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()

    output.append(f"-- premium_snapshots: {len(rows)} rows (last {days} days)")

    batch_size = 1000
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        output.append(f"-- Batch {i//batch_size + 1}: rows {i+1}-{min(i+batch_size, len(rows))}")
        for row in batch:
            values = []
            for val in row:
                if val is None:
                    values.append('NULL')
                elif isinstance(val, (int, float)):
                    values.append(str(val))
                elif isinstance(val, datetime):
                    values.append(f"'{val.isoformat()}'")
                else:
                    escaped = str(val).replace("'", "''")
                    values.append(f"'{escaped}'")

            output.append(f"INSERT INTO premium_snapshots ({', '.join(columns)}) VALUES ({', '.join(values)});")
        output.append('')

    conn.close()

    # 写入文件
    output_path = os.path.join(os.path.dirname(__file__), 'data', 'migration.sql')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output))

    size_mb = os.path.getsize(output_path) / 1024 / 1024
    print(f"导出完成: {output_path}")
    print(f"文件大小: {size_mb:.2f} MB")
    print(f"premium_snapshots 保留: {len(rows)} 条 (最近 {days} 天)")
    return output_path


def export_data_to_json(days: int = 7, all_data: bool = False):
    """导出为 JSON 格式（premium_snapshots 只保留最近 N 天）"""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    data = {}
    tables_to_export = ['funds', 'fund_holdings', 'user_watchlist', 'user_alerts']

    for table in tables_to_export:
        cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()
        data[table] = [dict(row) for row in rows]

    # premium_snapshots - 只保留最近 N 天（或用 --all 导出全部）
    if all_data:
        cursor.execute("SELECT * FROM premium_snapshots")
    else:
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(
            f"SELECT * FROM premium_snapshots WHERE snapshot_time >= '{cutoff_date}'"
        )
    rows = cursor.fetchall()
    data['premium_snapshots'] = [dict(row) for row in rows]

    conn.close()

    output_path = os.path.join(os.path.dirname(__file__), 'data', 'migration.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    size_mb = os.path.getsize(output_path) / 1024 / 1024
    print(f"导出完成: {output_path}")
    print(f"文件大小: {size_mb:.2f} MB")
    print(f"premium_snapshots 保留: {len(rows)} 条 (最近 {days} 天)")
    return output_path


def print_schema():
    """打印数据库 schema"""
    schema = get_db_schema()
    print(schema)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--schema', action='store_true', help='打印 schema')
    parser.add_argument('--export', action='store_true', help='导出为 SQL')
    parser.add_argument('--json', action='store_true', help='导出为 JSON')
    parser.add_argument('--days', type=int, default=7, help='保留最近 N 天的 premium_snapshots')
    parser.add_argument('--all', action='store_true', help='导出全部数据（不限制天数）')
    args = parser.parse_args()

    if args.schema:
        print_schema()
    elif args.export:
        export_data_to_sql(args.days, args.all)
    elif args.json:
        export_data_to_json(args.days, args.all)
    else:
        print("用法:")
        print("  python migrate_to_d1.py --schema")
        print("  python migrate_to_d1.py --export [--days 7]")
        print("  python migrate_to_d1.py --json [--days 7]")
