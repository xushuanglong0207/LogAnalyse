from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import redis
from .config import get_settings

settings = get_settings()

# PostgreSQL/SQLite 数据库连接
engine = create_engine(
    settings.database_url,
    poolclass=StaticPool if "sqlite" in settings.database_url else None,
    echo=settings.debug,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    future=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Redis 连接 - 可选
try:
    if settings.use_redis:
        redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    else:
        redis_client = None
except Exception:
    redis_client = None


# 数据库依赖注入
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Redis 依赖注入
def get_redis():
    if redis_client is not None:
        return redis_client
    return None 