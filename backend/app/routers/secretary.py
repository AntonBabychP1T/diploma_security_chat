from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional
from app.core.database import get_db
from app.services.secretary_service import SecretaryService
from app.routers.auth import get_current_user
from app.models.user import User
from app.models.chat import Chat, Message

router = APIRouter(prefix="/secretary", tags=["Secretary Agent"])

class SecretaryQuery(BaseModel):
    query: str
    chat_id: Optional[int] = None

class SecretaryResponse(BaseModel):
    response: str
    chat_id: int

@router.post("/ask", response_model=SecretaryResponse)
async def ask_secretary(
    request: SecretaryQuery,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Process a natural language query via the Secretary Agent with chat history.
    """
    # Create or get chat
    chat_id = request.chat_id
    if not chat_id:
        # Create new secretary chat
        new_chat = Chat(user_id=user.id, title="Secretary Chat")
        db.add(new_chat)
        await db.flush()  # Get the ID without committing yet
        chat_id = new_chat.id
    else:
        # Verify chat exists and belongs to user
        result = await db.execute(
            select(Chat).where(Chat.id == chat_id, Chat.user_id == user.id)
        )
        chat = result.scalar_one_or_none()
        if not chat:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Chat not found")
    
    # Get chat history
    history = []
    result = await db.execute(
        select(Message)
        .where(Message.chat_id == chat_id)
        .order_by(Message.created_at.asc())
    )
    messages = result.scalars().all()
    for msg in messages[-12:]:
        history.append({"role": msg.role, "content": msg.content})
    
    # Save user message
    user_message = Message(
        chat_id=chat_id,
        role="user",
        content=request.query
    )
    db.add(user_message)
    
    # Process request
    service = SecretaryService(db, user.id)
    response = await service.process_request(request.query, history)
    
    # Save assistant response
    assistant_message = Message(
        chat_id=chat_id,
        role="assistant",
        content=response
    )
    db.add(assistant_message)
    
    # Commit all changes
    await db.commit()
    
    return SecretaryResponse(response=response, chat_id=chat_id)

@router.get("/accounts")
async def get_accounts(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all connected accounts (Google and Microsoft).
    """
    service = SecretaryService(db, user.id)
    accounts = await service.get_connected_accounts()
    google = [{"id": acc.id, "email": acc.email, "label": acc.label} for acc in accounts["google"]]
    microsoft = [{"id": acc.id, "email": acc.email, "label": acc.label} for acc in accounts["microsoft"]]
    return {"google": google, "microsoft": microsoft}
