from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.digest_engine import DigestEngine
from app.services.action_executor import ActionExecutor
from app.models.digest_models import ActionStatus
import logging

router = APIRouter(prefix="/digest", tags=["digest"])
logger = logging.getLogger(__name__)

@router.post("/run")
async def manual_run_digest(user_id: int, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """
    Trigger a manual digest run for a user.
    """
    # Verify user exists? 
    # For internal use we can skip auth or use simple key if needed. 
    # Assuming this is called by admin or authenticated user.
    # For now, just run it.
    
    engine = DigestEngine(db, user_id)
    result = await engine.run_digest()
    return result

@router.post("/action/{action_id}/execute")
async def execute_action(action_id: int, user_id: int, db: AsyncSession = Depends(get_db)):
    """
    Execute a specific action proposal.
    """
    # Need access token.
    # We should get it from DB (GoogleAccount) inside ActionExecutor or pass it here.
    # ActionExecutor.execute_action takes access_token.
    # So we need to fetch it first.
    
    from app.models.google_account import GoogleAccount
    from sqlalchemy import select
    from app.services.google_auth_service import GoogleAuthService

    stmt = select(GoogleAccount).where(GoogleAccount.user_id == user_id)
    account = (await db.execute(stmt)).scalar_one_or_none()
    
    if not account:
        raise HTTPException(status_code=400, detail="No linked Google account")
        
    # Refresh token logic (duplicate from engine, effectively)
    token_info = await GoogleAuthService.refresh_access_token(account.refresh_token)
    access_token = token_info["access_token"]
    account.access_token = access_token
    await db.commit()

    executor = ActionExecutor(db, user_id)
    success = await executor.execute_action(action_id, access_token)
    
    if success:
        return {"status": "executed"}
    else:
        raise HTTPException(status_code=500, detail="Action execution failed")
