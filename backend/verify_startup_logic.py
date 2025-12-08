import sys
import os
import asyncio
from sqlalchemy import select

# Add current dir to path so we can import app
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.models.invite import Invite

async def check_invites():
    try:
        async with SessionLocal() as db:
            result = await db.execute(select(Invite))
            invites = result.scalars().all()
            print(f"Total invites: {len(invites)}")
            for i in invites:
                print(f"- {i.code} (Used: {i.is_used})")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # If on Windows, we might need a specific loop policy
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(check_invites())
