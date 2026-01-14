from datetime import timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError, jwt
import logging

from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token, SECRET_KEY, ALGORITHM, oauth2_scheme
from app.models.user import User
from app.models.invite import InviteCode
from pydantic import BaseModel, EmailStr
from datetime import datetime

logger = logging.getLogger("uvicorn.error")
router = APIRouter(prefix="/auth", tags=["auth"])

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    invite_code: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    id: int
    email: str
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    logger.info(f"=== REGISTRATION REQUEST ===")
    logger.info(f"Email: {user_data.email}")
    
    try:
        # Check if user exists
        result = await db.execute(select(User).where(User.email == user_data.email))
        existing = result.scalar_one_or_none()
        
        if existing:
            logger.warning(f"User already exists: {user_data.email}")
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Check invite
        result = await db.execute(select(InviteCode).where(InviteCode.code == user_data.invite_code))
        invite = result.scalar_one_or_none()

        if not invite:
            logger.warning(f"Invalid invite code: {user_data.invite_code}")
            raise HTTPException(status_code=400, detail="Invalid invite code")
        
        if invite.is_used:
            logger.warning(f"Invite code already used: {user_data.invite_code}")
            raise HTTPException(status_code=400, detail="Invite code already used")
            
        if invite.expires_at and invite.expires_at < datetime.utcnow():
            logger.warning(f"Invite code expired: {user_data.invite_code}")
            raise HTTPException(status_code=400, detail="Invite code expired")

        # Hash password
        logger.info("Hashing password...")
        hashed_pw = get_password_hash(user_data.password)
        logger.info("Password hashed successfully")
        
        # Create user
        logger.info("Creating user in database...")
        new_user = User(email=user_data.email, hashed_password=hashed_pw)
        db.add(new_user)
        await db.flush() # Get ID for invite linking
        
        # Mark invite as used
        invite.is_used = True
        invite.used_at = datetime.utcnow()
        invite.used_by_user_id = new_user.id
        
        await db.commit()
        await db.refresh(new_user)
        logger.info(f"✅ User created successfully with ID: {new_user.id}")
        
        return new_user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Registration error: {type(e).__name__}: {str(e)}")
        logger.exception("Full traceback:")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    logger.info(f"=== LOGIN REQUEST ===")
    logger.info(f"Username: {form_data.username}")
    
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning(f"Login failed for: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.email})
    logger.info(f"✅ Login successful for: {user.email}")
    return {"access_token": access_token, "token_type": "bearer"}

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user

async def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    return current_user

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/change-password")
async def change_password(
    passwords: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify current password before allowing update
    if not verify_password(passwords.current_password, current_user.hashed_password):
        logger.warning(f"Password change failed: incorrect current password for user {current_user.email}")
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    try:
        current_user.hashed_password = get_password_hash(passwords.new_password)
        await db.commit()
        await db.refresh(current_user)
        logger.info(f"Password updated successfully for user {current_user.email}")
        return {"detail": "Password updated successfully"}
    except Exception as e:
        logger.error(f"Password change error for user {current_user.email}: {type(e).__name__}: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update password")
