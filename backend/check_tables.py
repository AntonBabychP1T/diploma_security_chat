import asyncio
from sqlalchemy import text
from app.core.database import SessionLocal

async def check_tables():
    async with SessionLocal() as db:
        result = await db.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
        tables = result.scalars().all()
        print("Tables:", tables)

if __name__ == "__main__":
    asyncio.run(check_tables())
