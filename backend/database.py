import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

# 数据库路径 — 优先使用环境变量，否则默认本地 data 目录
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(os.path.dirname(__file__), 'data', 'qdii.db')}")
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# SQLite pragma 配置（WSL 兼容）
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    # 禁用 WAL 模式（WSL 挂载 Windows 驱动时不支持）
    cursor.execute("PRAGMA journal_mode=DELETE")
    cursor.execute("PRAGMA encoding='UTF-8'")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    import models
    models.Base.metadata.create_all(bind=engine)
