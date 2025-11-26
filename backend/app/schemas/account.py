from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Literal

class AccountLabelUpdate(BaseModel):
    """Schema for updating account label"""
    label: str
    
    @field_validator('label')
    @classmethod
    def validate_label(cls, v: str) -> str:
        allowed = ['personal', 'work', 'other']
        if v not in allowed:
            raise ValueError(f'Label must be one of: {allowed}')
        return v

class AccountResponse(BaseModel):
    """Schema for account response"""
    id: int
    email: str
    label: str
    is_default: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
