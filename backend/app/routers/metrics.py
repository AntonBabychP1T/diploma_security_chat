from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.metrics_service import MetricsService
from app.routers.auth import get_current_admin_user, get_current_user
from app.models.user import User

router = APIRouter(prefix="/metrics", tags=["metrics"])

@router.get("")
async def get_recent_metrics(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Metrics visible to any authenticated user (used by dashboard)."""
    service = MetricsService(db)
    return await service.get_recent_metrics()

@router.get("/global")
async def get_global_metrics(db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin_user)):
    service = MetricsService(db)
    return await service.get_global_stats()

@router.get("/leaderboard")
async def get_leaderboard(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = MetricsService(db)
    return await service.get_model_leaderboard()
