import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/qdii.db")
JISILI_COOKIE = os.getenv("JISILI_COOKIE", "")
REFRESH_INTERVAL_CN = int(os.getenv("REFRESH_INTERVAL_CN", "5"))
REFRESH_INTERVAL_HK = int(os.getenv("REFRESH_INTERVAL_HK", "10"))
REFRESH_INTERVAL_US = int(os.getenv("REFRESH_INTERVAL_US", "15"))
REFRESH_INTERVAL_PREMIUM = int(os.getenv("REFRESH_INTERVAL_PREMIUM", "10"))
REFRESH_INTERVAL_STATUS = int(os.getenv("REFRESH_INTERVAL_STATUS", "600"))
REFRESH_INTERVAL_NAV = int(os.getenv("REFRESH_INTERVAL_NAV", "1800"))
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
