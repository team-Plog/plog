from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

DATABASE_URL = "sqlite:///./sqlite-data/metric.db"
ASYNC_DATABASE_URL = "sqlite+aiosqlite:///./sqlite-data/metric.db"

# Sync engine (기존)
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False},
    pool_size=20,           # 기본 연결 풀 크기
    max_overflow=30,        # 초과 연결 허용
    pool_timeout=30,        # 연결 대기 시간
    pool_recycle=3600       # 연결 재사용 시간
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Async engine (새로 추가)
async_engine = create_async_engine(
    ASYNC_DATABASE_URL, connect_args={"check_same_thread": False}
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()
