from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class MemoryCreate(BaseModel):
    category: str = Field(..., description="profile | preference | project | constraint | other")
    key: str
    value: str
    confidence: Optional[float] = 0.7


class Memory(BaseModel):
    id: int
    user_id: int
    category: str
    key: str
    value: str
    confidence: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
