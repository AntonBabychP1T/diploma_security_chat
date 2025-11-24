import asyncio
from sqlalchemy import text
from app.core.database import SessionLocal

async def migrate():
    async with SessionLocal() as db:
        print("Migrating database...")
        try:
            # Check if column exists first to avoid error
            # SQLite doesn't support IF NOT EXISTS for columns easily in one statement
            # But we can just try and catch
            await db.execute(text("ALTER TABLE chats ADD COLUMN user_id INTEGER;"))
            await db.commit()
            print("✅ Added user_id column to chats")
        except Exception as e:
            if "duplicate column name" in str(e):
                print("ℹ️ Column user_id already exists")
            else:
                print(f"❌ Error adding column: {e}")

        # Also check if we need to add user_id to messages? 
        # The model for Message doesn't have user_id, it links to Chat. So that's fine.

if __name__ == "__main__":
    asyncio.run(migrate())
