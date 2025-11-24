from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import bcrypt
import logging

logger = logging.getLogger("uvicorn.error")

# Use a secure secret key in production!
SECRET_KEY = "YOUR_SUPER_SECRET_KEY_CHANGE_THIS" 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 days

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash using bcrypt."""
    try:
        # Encode to bytes and truncate to 72 bytes
        password_bytes = plain_password.encode('utf-8')[:72]
        hashed_bytes = hashed_password.encode('utf-8')
        
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception as e:
        logger.error(f"Password verification failed: {e}")
        return False

def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    logger.info(f"Hashing password (length: {len(password)})")
    
    try:
        # Encode to bytes and truncate to 72 bytes (bcrypt limit)
        password_bytes = password.encode('utf-8')[:72]
        logger.info(f"Password truncated to {len(password_bytes)} bytes")
        
        # Generate salt and hash
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password_bytes, salt)
        
        logger.info("Password hashed successfully")
        # Return as string
        return hashed.decode('utf-8')
    except Exception as e:
        logger.error(f"Password hashing failed: {type(e).__name__}: {str(e)}")
        raise

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
