from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.core.database import SessionLocal
from app.schemas.chat import Chat, ChatCreate, ChatRequest, Message, ChatUpdate
from app.services.chat_service import ChatService
from app.services.memory_service import MemoryService
from app.routers.auth import get_current_user
from app.models.user import User
import asyncio
import json

router = APIRouter(prefix="/chats", tags=["chats"])

@router.post("", response_model=Chat)
async def create_chat(chat: ChatCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = ChatService(db, user_id=current_user.id)
    return await service.create_chat(chat)

@router.get("", response_model=List[Chat])
async def get_chats(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = ChatService(db, user_id=current_user.id)
    return await service.get_chats()

@router.get("/{chat_id}", response_model=Chat)
async def get_chat(chat_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = ChatService(db, user_id=current_user.id)
    chat = await service.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat

@router.patch("/{chat_id}", response_model=Chat)
async def update_chat(chat_id: int, chat_data: ChatCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = ChatService(db, user_id=current_user.id)
    chat = await service.update_chat(chat_id, chat_data)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat

@router.delete("/{chat_id}")
async def delete_chat(chat_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = ChatService(db, user_id=current_user.id)
    success = await service.delete_chat(chat_id)
    if not success:
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"status": "ok"}

@router.post("/{chat_id}/messages", response_model=Message)
async def send_message(chat_id: int, request: ChatRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = ChatService(db, user_id=current_user.id)
    try:
        assistant_message = await service.send_message(
            chat_id=chat_id, 
            content=request.message,
            style=request.style or "default",
            provider_name=request.provider or "openai",
            model=request.model
        )

        # Schedule memory extraction in background to keep latency low
        async def run_memory_update(user_id: int, fragment: str):
            async with SessionLocal() as session:
                mem_service = MemoryService(session, user_id)
                await mem_service.update_store_from_extractor(fragment)

        dialog_fragment = f"user: {request.message}\nassistant: {assistant_message.content}"
        background_tasks.add_task(run_memory_update, current_user.id, dialog_fragment)

        return assistant_message
    except ValueError:
        raise HTTPException(status_code=404, detail="Chat not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{chat_id}/messages/stream")
async def send_message_stream(
    chat_id: int,
    request: ChatRequest,
    fastapi_request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = ChatService(db, user_id=current_user.id)

    try:
        stream_gen = await service.send_message_stream(
            chat_id=chat_id,
            content=request.message,
            style=request.style or "default",
            provider_name=request.provider or "openai",
            model=request.model,
            fastapi_request=fastapi_request,
            background_tasks=background_tasks
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Chat not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return StreamingResponse(stream_gen, media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive"
    })
