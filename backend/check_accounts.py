import asyncio
import sys
import os
from sqlalchemy import select

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import async_session_factory
from app.models.google_account import GoogleAccount

async def check_accounts():
    async with async_session_factory() as db:
        result = await db.execute(select(GoogleAccount))
        accounts = result.scalars().all()
        print(f"Found {len(accounts)} accounts:")
        for acc in accounts:
            print(f"- ID: {acc.id}, Email: {acc.email}, Label: '{acc.label}'")

if __name__ == "__main__":
    asyncio.run(check_accounts())
