from app.models.sqlite.database import SessionLocal, AsyncSessionLocal

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_async_db():
    async with AsyncSessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()

__all__ = ['get_db', 'get_async_db']