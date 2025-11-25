from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.services.google_auth_service import GoogleAuthService
from app.models.google_account import GoogleAccount
from app.routers.auth import get_current_user # Assuming this exists
from app.models.user import User
from datetime import datetime, timedelta
import logging
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/auth/google", tags=["Google Auth"])

@router.get("/login")
async def login(request: Request, user: User = Depends(get_current_user)):
    """
    Redirects user to Google Login.
    State parameter encodes user_id to link account on callback.
    """
    # Simple state: user_id. In production, sign this to prevent CSRF/tampering.
    state = str(user.id) 
    redirect_uri = f"{settings.FRONTEND_PUBLIC_URL.rstrip('/')}/api/auth/google/callback"
    auth_url = GoogleAuthService.get_authorization_url(state, redirect_uri)
    # TODO: sign state for CSRF protection in production
    # Return JSON so frontend can fetch with auth header then redirect
    if request.query_params.get("redirect") == "true":
        return RedirectResponse(auth_url)
    return {"url": auth_url}

@router.get("/callback")
async def callback(code: str, state: str, db: AsyncSession = Depends(get_db)):
    """
    Handles Google OAuth callback.
    Exchanges code for tokens and saves to DB.
    """
    try:
        user_id = int(state)
        # Verify user exists? (Optional, FK constraint will handle it but good for UX)
        
        redirect_uri = f"{settings.FRONTEND_PUBLIC_URL.rstrip('/')}/api/auth/google/callback"
        token_data = await GoogleAuthService.exchange_code_for_token(code, redirect_uri)
        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)
        
        user_info = await GoogleAuthService.get_user_info(access_token)
        email = user_info["email"]
        
        # Check if account already exists
        query = select(GoogleAccount).where(
            GoogleAccount.user_id == user_id,
            GoogleAccount.email == email
        )
        result = await db.execute(query)
        existing_account = result.scalar_one_or_none()
        
        if existing_account:
            existing_account.access_token = access_token
            if refresh_token:
                existing_account.refresh_token = refresh_token
            existing_account.token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
            await db.commit()
        else:
            # Create new account
            new_account = GoogleAccount(
                user_id=user_id,
                email=email,
                access_token=access_token,
                refresh_token=refresh_token,
                token_expiry=datetime.utcnow() + timedelta(seconds=expires_in),
                label="personal", # Default, user can change later
                is_default=False
            )
            db.add(new_account)
            await db.commit()

        # Redirect back to chat; optionally include status for UI banners
        return RedirectResponse(f"{settings.FRONTEND_PUBLIC_URL.rstrip('/')}/?google_status=connected&email={email}")
            
    except Exception as e:
        logger.error(f"Google Auth Error: {e}")
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")
