from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.routers.auth import get_current_user
from app.schemas.memory import Memory as MemorySchema, MemoryCreate
from app.services.memory_service import MemoryService
from app.models.user import User

router = APIRouter(prefix="/memories", tags=["memories"])


@router.get("", response_model=list[MemorySchema])
async def list_memories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = MemoryService(db, user_id=current_user.id)
    memories = await service.get_memories()
    return memories


@router.post("", response_model=MemorySchema)
async def create_memory(
    payload: MemoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = MemoryService(db, user_id=current_user.id)
    return await service.add_memory(
        category=payload.category,
        key=payload.key,
        value=payload.value,
        confidence=payload.confidence or 0.7
    )


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = MemoryService(db, user_id=current_user.id)
    success = await service.delete_memory(memory_id)
    if not success:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"status": "ok"}
