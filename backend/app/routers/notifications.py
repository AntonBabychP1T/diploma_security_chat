from fastapi import APIRouter, Depends, Body, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.notification_service import NotificationService
from app.routers.auth import get_current_user
from app.models.user import User
from app.core.config import get_settings
import logging

router = APIRouter(prefix="/notifications", tags=["notifications"])
logger = logging.getLogger(__name__)
settings = get_settings()

@router.get("/vapid-public-key")
async def get_vapid_public_key():
    if not settings.VAPID_PUBLIC_KEY:
        raise HTTPException(status_code=500, detail="VAPID public key not configured")
    return {"publicKey": settings.VAPID_PUBLIC_KEY}

@router.post("/subscribe")
async def subscribe(
    request: Request,
    subscription: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    service = NotificationService(db)
    user_agent = request.headers.get("user-agent")
    try:
        await service.subscribe(user.id, subscription, user_agent)
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
