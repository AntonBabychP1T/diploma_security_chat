from typing import Protocol, List, Optional, runtime_checkable
from datetime import datetime
from app.schemas.secretary import EmailMessage, CalendarEvent, TimeSlot, EmailFilters

@runtime_checkable
class MailCalendarProvider(Protocol):
    async def list_emails(self, filters: Optional[EmailFilters] = None) -> List[EmailMessage]:
        ...

    async def list_events(self, time_min: datetime, time_max: datetime) -> List[CalendarEvent]:
        ...

    async def find_free_slots(self, time_min: datetime, time_max: datetime, duration_minutes: int = 30) -> List[TimeSlot]:
        ...

    async def send_email(self, to: List[str], subject: str, body: str) -> Dict[str, Any]:
        ...

    async def create_event(self, summary: str, start_time: datetime, end_time: datetime, attendees: List[str]) -> Dict[str, Any]:
        ...
