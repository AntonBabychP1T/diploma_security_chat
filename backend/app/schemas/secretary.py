from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime

class EmailFilters(BaseModel):
    is_unread: Optional[bool] = None
    sender: Optional[str] = None
    subject_keyword: Optional[str] = None
    max_results: int = 10

class EmailMessage(BaseModel):
    id: str
    thread_id: str
    subject: str
    sender: str
    snippet: str
    date: datetime
    is_read: bool
    link: Optional[str] = None

class CalendarEvent(BaseModel):
    id: str
    summary: str
    start: datetime
    end: datetime
    location: Optional[str] = None
    description: Optional[str] = None
    html_link: Optional[str] = None
    attendees: List[str] = []

class TimeSlot(BaseModel):
    start: datetime
    end: datetime
    duration_minutes: int
