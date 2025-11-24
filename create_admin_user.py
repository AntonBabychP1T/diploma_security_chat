"""
Script to create an admin user or promote existing user to admin
"""
import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.core.security import get_password_hash
from sqlalchemy import select


async def create_admin_user():
    """Create an admin user if it doesn't exist, or promote first user to admin"""
    
    email = input("Enter admin email (default: admin@example.com): ").strip() or "admin@example.com"
    password = input("Enter admin password (default: admin123): ").strip() or "admin123"
    
    async with AsyncSessionLocal() as db:
        # Check if user exists
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        if user:
            # Promote to admin
            user.is_admin = True
            await db.commit()
            print(f"✅ User {email} promoted to admin!")
        else:
            # Create new admin user
            hashed_pw = get_password_hash(password)
            admin_user = User(
                email=email,
                hashed_password=hashed_pw,
                is_admin=True
            )
            db.add(admin_user)
            await db.commit()
            print(f"✅ Admin user created: {email}")
    
    print(f"\nYou can now login with:")
    print(f"  Email: {email}")
    print(f"  Password: {password}")
    print(f"\nAccess admin dashboard at: http://localhost:5173/admin")


if __name__ == "__main__":
    asyncio.run(create_admin_user())
