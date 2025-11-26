from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.services.microsoft_auth_service import MicrosoftAuthService
from app.models.microsoft_account import MicrosoftAccount
from app.routers.auth import get_current_user
from app.models.user import User
from app.schemas.account import AccountLabelUpdate, AccountResponse
from datetime import datetime, timedelta
import logging
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/auth/microsoft", tags=["Microsoft Auth"])

@router.get("/login")
async def login(request: Request, user: User = Depends(get_current_user)):
    """
    Redirects user to Microsoft Login.
    """
    state = str(user.id)
    # Use configured redirect URI or construct one
    redirect_uri = settings.MICROSOFT_REDIRECT_URI or f"{settings.FRONTEND_PUBLIC_URL.rstrip('/')}/api/auth/microsoft/callback"
    
    try:
        auth_url = MicrosoftAuthService.get_authorization_url(state, redirect_uri)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    if request.query_params.get("redirect") == "true":
        return RedirectResponse(auth_url)
    return {"url": auth_url}

@router.get("/callback")
async def callback(code: str, state: str, db: AsyncSession = Depends(get_db)):
    """
    Handles Microsoft OAuth callback.
    """
    try:
        user_id = int(state)
        
        redirect_uri = settings.MICROSOFT_REDIRECT_URI or f"{settings.FRONTEND_PUBLIC_URL.rstrip('/')}/api/auth/microsoft/callback"
        
        token_data = await MicrosoftAuthService.exchange_code_for_token(code, redirect_uri)
        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)
        
        user_info = await MicrosoftAuthService.get_user_profile(access_token)
        email = user_info.get("mail") or user_info.get("userPrincipalName")
        display_name = user_info.get("displayName")
        
        # Check if account already exists
        query = select(MicrosoftAccount).where(
            MicrosoftAccount.user_id == user_id,
            MicrosoftAccount.email == email
        )
        result = await db.execute(query)
        existing_account = result.scalar_one_or_none()
        
        if existing_account:
            existing_account.access_token = access_token
            if refresh_token:
                existing_account.refresh_token = refresh_token
            existing_account.token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
            existing_account.display_name = display_name
            await db.commit()
        else:
            new_account = MicrosoftAccount(
                user_id=user_id,
                email=email,
                display_name=display_name,
                access_token=access_token,
                refresh_token=refresh_token,
                token_expiry=datetime.utcnow() + timedelta(seconds=expires_in),
                label="work", # Default
                is_default=False,
                tenant_id=settings.MICROSOFT_TENANT_ID
            )
            db.add(new_account)
            await db.commit()

        return RedirectResponse(f"{settings.FRONTEND_PUBLIC_URL.rstrip('/')}/?microsoft_status=connected&email={email}")
            
    except Exception as e:
        logger.error(f"Microsoft Auth Error: {e}")
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")

@router.delete("/accounts/{account_id}")
async def delete_microsoft_account(
    account_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a Microsoft account.
    """
    result = await db.execute(
        select(MicrosoftAccount)
        .where(MicrosoftAccount.id == account_id, MicrosoftAccount.user_id == user.id)
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    await db.delete(account)
    await db.commit()
    
    logger.info(f"User {user.id} deleted Microsoft account {account_id}")
    return {"status": "ok", "message": "Account deleted successfully"}

@router.patch("/accounts/{account_id}", response_model=AccountResponse)
async def update_microsoft_account_label(
    account_id: int,
    update_data: AccountLabelUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update Microsoft account label.
    """
    result = await db.execute(
        select(MicrosoftAccount)
        .where(MicrosoftAccount.id == account_id, MicrosoftAccount.user_id == user.id)
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    account.label = update_data.label
    await db.commit()
    await db.refresh(account)
    
    logger.info(f"User {user.id} updated Microsoft account {account_id} label to {update_data.label}")
    return AccountResponse.model_validate(account)
