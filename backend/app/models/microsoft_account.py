from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, Boolean, ForeignKey, DateTime
from datetime import datetime
from typing import Optional
from app.core.database import Base

class MicrosoftAccount(Base):
    __tablename__ = "microsoft_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    email: Mapped[str] = mapped_column(String, index=True, nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # "work", "personal", etc.
    label: Mapped[str] = mapped_column(String, default="work")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # OAuth tokens
    access_token: Mapped[str] = mapped_column(String, nullable=False)
    refresh_token: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    token_expiry: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Microsoft specific
    tenant_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
