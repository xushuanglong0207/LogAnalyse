from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import redis
from .config import get_settings

settings = get_settings()

# PostgreSQL 数据库连接
engine = create_engine(
    settings.database_url,
    poolclass=StaticPool,
    echo=settings.debug,
    future=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Redis 连接
redis_client = redis.from_url(settings.redis_url, decode_responses=True)


# 数据库依赖注入
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Redis 依赖注入
def get_redis():
    return redis_client 