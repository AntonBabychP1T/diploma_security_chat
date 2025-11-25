import httpx
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from app.schemas.secretary import EmailMessage, CalendarEvent, TimeSlot, EmailFilters

class GoogleWorkspaceClient:
    GMAIL_API_URL = "https://gmail.googleapis.com/gmail/v1/users/me"
    CALENDAR_API_URL = "https://www.googleapis.com/calendar/v3"

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }

    async def list_emails(self, filters: Optional[EmailFilters] = None) -> List[EmailMessage]:
        query_parts = []
        max_results = 10
        
        if filters:
            if filters.is_unread:
                query_parts.append("is:unread")
            if filters.sender:
                query_parts.append(f"from:{filters.sender}")
            if filters.subject_keyword:
                query_parts.append(f"subject:{filters.subject_keyword}")
            if filters.max_results:
                max_results = filters.max_results

        q = " ".join(query_parts)
        
        params = {"maxResults": max_results, "q": q}
        
        async with httpx.AsyncClient() as client:
            # 1. List IDs
            response = await client.get(f"{self.GMAIL_API_URL}/messages", headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            messages_meta = data.get("messages", [])
            
            results = []
            # 2. Batch get details (in parallel ideally, but sequential for simplicity first)
            # Optimization: Use batch request or parallel gather
            # For now, simple loop
            for meta in messages_meta:
                msg_id = meta["id"]
                detail_resp = await client.get(f"{self.GMAIL_API_URL}/messages/{msg_id}", headers=self.headers)
                if detail_resp.status_code == 200:
                    msg_data = detail_resp.json()
                    parsed = self._parse_email(msg_data)
                    if parsed:
                        results.append(parsed)
            
            return results

    def _parse_email(self, data: Dict[str, Any]) -> Optional[EmailMessage]:
        try:
            payload = data.get("payload", {})
            headers = payload.get("headers", [])
            snippet = data.get("snippet", "")
            internal_date = int(data.get("internalDate", 0)) / 1000.0
            
            subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), "(No Subject)")
            sender = next((h["value"] for h in headers if h["name"].lower() == "from"), "Unknown")
            
            label_ids = data.get("labelIds", [])
            is_read = "UNREAD" not in label_ids
            
            return EmailMessage(
                id=data["id"],
                thread_id=data["threadId"],
                subject=subject,
                sender=sender,
                snippet=snippet,
                date=datetime.fromtimestamp(internal_date),
                is_read=is_read,
                link=f"https://mail.google.com/mail/u/0/#inbox/{data['id']}"
            )
        except Exception:
            return None

    async def list_events(self, time_min: datetime, time_max: datetime) -> List[CalendarEvent]:
        params = {
            "timeMin": time_min.isoformat() + "Z", # Ensure UTC
            "timeMax": time_max.isoformat() + "Z",
            "singleEvents": "true",
            "orderBy": "startTime"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.CALENDAR_API_URL}/calendars/primary/events", headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            items = data.get("items", [])
            
            events = []
            for item in items:
                # Skip cancelled
                if item.get("status") == "cancelled":
                    continue
                    
                start = item.get("start", {})
                end = item.get("end", {})
                
                # Handle all-day events (date only, no dateTime)
                start_dt = self._parse_calendar_date(start)
                end_dt = self._parse_calendar_date(end)
                
                if not start_dt or not end_dt:
                    continue

                attendees = [a.get("email") for a in item.get("attendees", []) if a.get("email")]

                events.append(CalendarEvent(
                    id=item["id"],
                    summary=item.get("summary", "(No Title)"),
                    start=start_dt,
                    end=end_dt,
                    location=item.get("location"),
                    description=item.get("description"),
                    html_link=item.get("htmlLink"),
                    attendees=attendees
                ))
            return events

    def _parse_calendar_date(self, date_obj: Dict[str, Any]) -> Optional[datetime]:
        if "dateTime" in date_obj:
            # ISO format with timezone usually
            try:
                return datetime.fromisoformat(date_obj["dateTime"].replace("Z", "+00:00"))
            except:
                return None
        elif "date" in date_obj:
            # YYYY-MM-DD
            try:
                return datetime.fromisoformat(date_obj["date"])
            except:
                return None
        return None

    async def find_free_slots(self, time_min: datetime, time_max: datetime, duration_minutes: int = 30) -> List[TimeSlot]:
        # Simple implementation: Get all events, find gaps
        events = await self.list_events(time_min, time_max)
        
        slots = []
        current_time = time_min
        
        # Sort events just in case (API usually does, but good to be safe)
        events.sort(key=lambda x: x.start)
        
        for event in events:
            # Check gap between current_time and event.start
            # Ensure we are comparing timezone-aware datetimes correctly
            # Assuming event.start is offset-aware if parsed correctly
            
            # Normalize current_time to event.start tz if needed, or convert both to UTC
            # For simplicity, let's assume UTC or compatible offsets
            
            if event.start > current_time:
                gap = event.start - current_time
                if gap >= timedelta(minutes=duration_minutes):
                    slots.append(TimeSlot(
                        start=current_time,
                        end=event.start,
                        duration_minutes=int(gap.total_seconds() / 60)
                    ))
            
            # Move current_time to end of event if it's later
            if event.end > current_time:
                current_time = event.end
        
        # Check gap after last event until time_max
        if time_max > current_time:
            gap = time_max - current_time
            if gap >= timedelta(minutes=duration_minutes):
                slots.append(TimeSlot(
                    start=current_time,
                    end=time_max,
                    duration_minutes=int(gap.total_seconds() / 60)
                ))
                
        return slots
