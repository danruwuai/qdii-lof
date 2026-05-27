"""
同步本地 SQLite 到 Cloudflare D1

用法:
  python sync_to_d1.py              # 增量同步（只同步 updated_at 之后的数据）
  python sync_to_d1.py --full       # 全量同步（清空后重新导入）
  python sync_to_d1.py --table funds  # 同步指定表
"""

import sqlite3
import os
import sys
import tempfile
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'qdii.db')
STATE_FILE = os.path.join(os.path.dirname(__file__), '.d1_sync_state')
D1_PROJECT = 'qdii-lof-db'

def get_last_sync():
    """读取上次同步时间"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return datetime.fromisoformat(f.read().strip())
    return None

def save_sync_state():
    """保存本次同步时间"""
    with open(STATE_FILE, 'w') as f:
        f.write(datetime.now().isoformat())

def generate_insert_sql(table, rows, columns):
    """生成 INSERT OR REPLACE SQL"""
    if not rows:
        return []
    sqls = []
    for row in rows:
        vals = []
        for v in row:
            if v is None:
                vals.append('NULL')
            elif isinstance(v, (int, float)):
                vals.append(str(v))
            elif isinstance(v, str):
                escaped = v.replace("'", "''")
                vals.append(f"'{escaped}'")
            elif isinstance(v, datetime):
                vals.append(f"'{v.isoformat()}'")
            else:
                vals.append(f"'{str(v)}'")
        sqls.append(f"INSERT OR REPLACE INTO {table} ({', '.join(columns)}) VALUES ({', '.join(vals)});")
    return sqls

def sync_table(table, full=False, since=None):
    """同步单张表"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 获取表结构
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [col[1] for col in cursor.fetchall()]
    pk_col = columns[0]  # 第一列通常是主键

    if full:
        # 全量同步
        cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()
        print(f"  {table}: FULL {len(rows)} rows")
    elif since:
        # 增量同步
        if 'updated_at' in columns:
            cursor.execute(f"SELECT * FROM {table} WHERE updated_at >= ?", [since.isoformat()])
        elif 'nav_date' in columns:
            cursor.execute(f"SELECT * FROM {table} WHERE nav_date >= ?", [since.strftime('%Y-%m-%d')])
        else:
            # 没有时间字段，全量同步
            cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()
        print(f"  {table}: DELTA {len(rows)} rows (since {since})")
    else:
        cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()
        print(f"  {table}: FULL {len(rows)} rows")

    conn.close()

    if not rows:
        return 0

    # 分批发送到 D1
    count = 0
    batch_size = 50
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        sqls = generate_insert_sql(table, batch, columns)
        sql_content = '\n'.join(sqls)

        # 写入临时文件
        tmp_fd, tmp_file = tempfile.mkstemp(suffix='.sql')
        os.close(tmp_fd)
        with open(tmp_file, 'w', encoding='utf-8') as f:
            f.write(sql_content)

        # 执行 wrangler d1 execute
        import subprocess
        import shutil
        wrangler_path = shutil.which('wrangler')
        if not wrangler_path:
            # Try common paths
            for p in ['/usr/local/bin/wrangler', '/usr/bin/wrangler', '/home/runner/.npm/bin/wrangler']:
                if os.path.exists(p):
                    wrangler_path = p
                    break

        if not wrangler_path:
            print(f"    ERROR: wrangler not found in PATH")
            continue

        result = subprocess.run(
            [wrangler_path, 'd1', 'execute', D1_PROJECT, '--remote', '--file', tmp_file],
            capture_output=True, timeout=120
        )

        if result.returncode != 0:
            print(f"    WARN batch {i//batch_size + 1} failed: {result.stderr[:200]}")
        else:
            count += len(batch)

        # 清理临时文件
        try:
            os.remove(tmp_file)
        except:
            pass

    return count

def main():
    full = '--full' in sys.argv
    table_filter = None
    if '--table' in sys.argv:
        idx = sys.argv.index('--table')
        if idx + 1 < len(sys.argv):
            table_filter = sys.argv[idx + 1]

    tables = ['funds', 'fund_holdings', 'premium_snapshots', 'user_watchlist', 'user_alerts']
    if table_filter:
        tables = [t for t in tables if t == table_filter]

    since = get_last_sync() if not full else None
    if since and not full:
        print(f"Last sync: {since}")
        print(f"Delta sync start...")

    total = 0
    for table in tables:
        try:
            count = sync_table(table, full=full, since=since)
            total += count
        except Exception as e:
            print(f"  {table} FAIL: {e}")

    print(f"\nSync done: {total} rows total")
    save_sync_state()
    print(f"Sync time saved: {datetime.now().isoformat()}")

    if total > 0:
        print("\nVerify with: wrangler d1 execute qdii-lof-db --remote --command \"SELECT COUNT(*) FROM funds\"")

if __name__ == '__main__':
    main()
