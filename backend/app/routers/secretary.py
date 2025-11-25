from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.core.database import get_db
from app.services.secretary_service import SecretaryService
from app.routers.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/secretary", tags=["Secretary Agent"])

class SecretaryQuery(BaseModel):
    query: str

class SecretaryResponse(BaseModel):
    response: str

@router.post("/ask", response_model=SecretaryResponse)
async def ask_secretary(
    request: SecretaryQuery,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Process a natural language query via the Secretary Agent.
    """
    service = SecretaryService(db, user.id)
    response = await service.process_request(request.query)
    return SecretaryResponse(response=response)
