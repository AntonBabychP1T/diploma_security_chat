from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, ForeignKey, DateTime, Text, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, index=True, nullable=True)
    title: Mapped[str] = mapped_column(String, default="New Chat")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    messages: Mapped[List["Message"]] = relationship(back_populates="chat", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"))
    role: Mapped[str] = mapped_column(String)  # user, assistant, system
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    meta_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True) # provider, tokens, latency, masked_used

    chat: Mapped["Chat"] = relationship(back_populates="messages")
