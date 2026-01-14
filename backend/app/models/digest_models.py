from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, ForeignKey, DateTime, Text, JSON, Integer, Boolean, BigInteger, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum

class ActionStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"

class ActionType(str, enum.Enum):
    ARCHIVE_PROMO = "ARCHIVE_PROMO"
    CREATE_DRAFT = "CREATE_DRAFT"
    CREATE_EVENT = "CREATE_EVENT"

class GmailSyncState(Base):
    __tablename__ = "gmail_sync_states"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    last_history_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    last_success_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_streak: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    full_sync_anchor: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationship to user if needed, assuming 'User' model exists and back_populates is set up
    # user: Mapped["User"] = relationship(back_populates="gmail_sync_state")

class EmailSnapshot(Base):
    __tablename__ = "email_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    gmail_message_id: Mapped[str] = mapped_column(String, index=True) # Unique per user efficiently enforced by app logic or composite index
    thread_id: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)
    
    sender: Mapped[Optional[str]] = mapped_column(String, nullable=True) # "from" is reserved keyword
    recipient: Mapped[Optional[str]] = mapped_column(String, nullable=True) # "to"
    subject: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    internal_date: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True) # ms epoch
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    label_ids: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    category: Mapped[str] = mapped_column(String, default="OTHER") # PROMO, IMPORTANT, OTHER
    
    has_attachments: Mapped[bool] = mapped_column(Boolean, default=False)
    attachments_meta: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True) # [{filename, mime, size}]

class DigestRun(Base):
    __tablename__ = "digest_runs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    
    start_history_id_used: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    
    created_chat_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_message_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    stats: Mapped[Optional[Dict[str, int]]] = mapped_column(JSON, nullable=True) # e.g. {"emails_scanned": 10, "promos_found": 2}
    status: Mapped[str] = mapped_column(String, default="SUCCESS") # SUCCESS, FAILED
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    action_proposals: Mapped[List["ActionProposal"]] = relationship(back_populates="digest_run", cascade="all, delete-orphan")

class ActionProposal(Base):
    __tablename__ = "action_proposals"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    digest_id: Mapped[int] = mapped_column(ForeignKey("digest_runs.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    
    type: Mapped[ActionType] = mapped_column(String) # ARCHIVE_PROMO, CREATE_DRAFT, CREATE_EVENT
    payload_json: Mapped[Dict[str, Any]] = mapped_column(JSON) # Action-specific data
    
    status: Mapped[ActionStatus] = mapped_column(String, default=ActionStatus.PENDING)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    digest_run: Mapped["DigestRun"] = relationship(back_populates="action_proposals")
