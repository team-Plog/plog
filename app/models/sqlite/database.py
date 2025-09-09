from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

DATABASE_URL = "sqlite:///./sqlite-data/metric.models"
ASYNC_DATABASE_URL = "sqlite+aiosqlite:///./sqlite-data/metric.models"

# Sync engine (기존)
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Async engine (새로 추가)
async_engine = create_async_engine(
    ASYNC_DATABASE_URL, connect_args={"check_same_thread": False}
)

AsyncSessionLocal = AsyncSession(async_engine)

Base = declarative_base()
