import asyncio
import secrets
import string
import sys
import os

# Add the parent directory to sys.path to allow imports from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.database import SessionLocal
from app.models.invite import InviteCode

def generate_code(length=12):
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

async def create_invites(count=10):
    async with SessionLocal() as db:
        print(f"Generating {count} invites...")
        created = []
        for _ in range(count):
            code = generate_code()
            invite = InviteCode(code=code)
            db.add(invite)
            created.append(code)
        
        await db.commit()
        print(f"Successfully created {len(created)} invites:")
        for code in created:
            print(f"- {code}")

if __name__ == "__main__":
    count = 10
    if len(sys.argv) > 1:
        try:
            count = int(sys.argv[1])
        except ValueError:
            print("Usage: python invite_manager.py [count]")
            sys.exit(1)
            
    asyncio.run(create_invites(count))
