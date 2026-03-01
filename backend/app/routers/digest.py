from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.google_account import GoogleAccount
from app.models.user import User
from app.routers.auth import get_current_user
from app.services.action_executor import ActionExecutor
from app.services.digest_engine import DigestEngine
from app.services.google_auth_service import GoogleAuthService

router = APIRouter(prefix="/digest", tags=["digest"])


@router.post("/run")
async def manual_run_digest(
    mode: Literal["poll", "morning", "evening"] = "poll",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    engine = DigestEngine(db, current_user.id)
    return await engine.run_digest(mode=mode)


@router.post("/action/{action_id}/execute")
async def execute_action(
    action_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(GoogleAccount).where(GoogleAccount.user_id == current_user.id)
    account = (await db.execute(stmt)).scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=400, detail="No linked Google account")

    token_info = await GoogleAuthService.refresh_access_token(account.refresh_token)
    access_token = token_info["access_token"]
    account.access_token = access_token
    await db.commit()

    executor = ActionExecutor(db, current_user.id)
    success = await executor.execute_action(action_id, access_token)
    if not success:
        raise HTTPException(status_code=500, detail="Action execution failed")

    return {"status": "executed"}
