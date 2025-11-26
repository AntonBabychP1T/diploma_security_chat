from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.core.database import get_db
from app.routers.auth import get_current_user
from app.models.user import User
from app.models.agent_settings import AgentSettings

router = APIRouter(prefix="/agent-settings", tags=["Agent Settings"])


class AgentSettingsResponse(BaseModel):
    custom_instructions: str

    class Config:
        from_attributes = True


class AgentSettingsUpdate(BaseModel):
    custom_instructions: str


@router.get("", response_model=AgentSettingsResponse)
async def get_agent_settings(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's agent settings.
    """
    result = await db.execute(
        select(AgentSettings).where(AgentSettings.user_id == user.id)
    )
    settings = result.scalar_one_or_none()
    
    if not settings:
        # Return default empty settings
        return AgentSettingsResponse(custom_instructions="")
    
    return AgentSettingsResponse(custom_instructions=settings.custom_instructions or "")


@router.put("", response_model=AgentSettingsResponse)
async def update_agent_settings(
    payload: AgentSettingsUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update or create agent settings for the current user.
    """
    result = await db.execute(
        select(AgentSettings).where(AgentSettings.user_id == user.id)
    )
    settings = result.scalar_one_or_none()
    
    if settings:
        # Update existing
        settings.custom_instructions = payload.custom_instructions
    else:
        # Create new
        settings = AgentSettings(
            user_id=user.id,
            custom_instructions=payload.custom_instructions
        )
        db.add(settings)
    
    await db.commit()
    await db.refresh(settings)
    
    return AgentSettingsResponse(custom_instructions=settings.custom_instructions or "")
