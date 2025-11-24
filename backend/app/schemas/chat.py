from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class MessageBase(BaseModel):
    role: str
    content: str

class MessageCreate(MessageBase):
    pass

class Message(MessageBase):
    id: int
    chat_id: int
    created_at: datetime
    meta_data: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

class ChatBase(BaseModel):
    title: Optional[str] = "New Chat"

class ChatCreate(ChatBase):
    pass

class ChatUpdate(ChatBase):
    pass

class Chat(ChatBase):
    id: int
    user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    messages: List[Message] = []

    class Config:
        from_attributes = True

class ChatRequest(BaseModel):
    message: str
    style: Optional[str] = "default"
    provider: Optional[str] = "openai"
    model: Optional[str] = None
