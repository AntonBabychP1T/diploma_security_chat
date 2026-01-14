import httpx
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import base64
import logging
from email.mime.text import MIMEText
from app.schemas.secretary import EmailMessage, CalendarEvent, TimeSlot, EmailFilters

logger = logging.getLogger(__name__)

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
                max_results = min(filters.max_results, 20)  # Cap at 20 to prevent excessive API calls

        q = " ".join(query_parts)
        
        params = {"maxResults": max_results, "q": q}
        
        async with httpx.AsyncClient() as client:
            # 1. List IDs
            response = await client.get(f"{self.GMAIL_API_URL}/messages", headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            messages_meta = data.get("messages", [])
            
            # 2. Fetch details in parallel
            import asyncio
            
            async def fetch_email(msg_id: str) -> Optional[EmailMessage]:
                try:
                    detail_resp = await client.get(f"{self.GMAIL_API_URL}/messages/{msg_id}", headers=self.headers)
                    if detail_resp.status_code == 200:
                        msg_data = detail_resp.json()
                        return self._parse_email(msg_data)
                except Exception as e:
                    logger.error(f"Error fetching email {msg_id}: {e}")
                return None
            
            tasks = [fetch_email(meta["id"]) for meta in messages_meta]
            results = await asyncio.gather(*tasks)
            
            return [r for r in results if r is not None]

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



    async def get_email(self, message_id: str) -> Optional[EmailMessage]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.GMAIL_API_URL}/messages/{message_id}", headers=self.headers)
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                return self._parse_email(response.json())
        except Exception as e:
            logger.error(f"Error getting email {message_id}: {e}")
            return None

    async def send_email(self, to: List[str], subject: str, body: str) -> Dict[str, Any]:
        message = MIMEText(body)
        message['to'] = ", ".join(to)
        message['subject'] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        payload = {'raw': raw}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.GMAIL_API_URL}/messages/send", headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()

    async def create_draft(self, to: List[str], subject: str, body: str) -> Dict[str, Any]:
        """Creates a draft email."""
        message = MIMEText(body)
        message['to'] = ", ".join(to)
        message['subject'] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        payload = {
            'message': {
                'raw': raw
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.GMAIL_API_URL}/drafts", headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()

    async def reply_email(self, message_id: str, body: str, reply_all: bool = False) -> Dict[str, Any]:
        # 1. Get original message to find threadId and headers
        original = await self.get_email(message_id)
        if not original:
            raise ValueError(f"Email {message_id} not found")

        # We need raw headers for In-Reply-To and References, which _parse_email might not give fully.
        # So let's fetch raw or just use threadId which is often enough for Gmail to group, 
        # but for proper threading standards we need headers.
        # For simplicity in this iteration, we rely on Gmail's threadId grouping 
        # but we MUST send In-Reply-To to be a proper reply.
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.GMAIL_API_URL}/messages/{message_id}?format=metadata", headers=self.headers)
            resp.raise_for_status()
            meta = resp.json()
            headers = meta.get("payload", {}).get("headers", [])
            
            msg_id_header = next((h["value"] for h in headers if h["name"].lower() == "message-id"), None)
            references = next((h["value"] for h in headers if h["name"].lower() == "references"), "")
            subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), "")
            
            if not subject.lower().startswith("re:"):
                subject = f"Re: {subject}"

            # Construct reply
            message = MIMEText(body)
            message['subject'] = subject
            
            # To/Cc logic would go here for reply_all, for now simple reply to sender
            # In a real app we'd parse 'Reply-To' or 'From'
            # For now, let's assume the user provides the recipient or we extract it? 
            # The interface in secretary_tools.py might need to handle 'to', 
            # but usually 'reply' implies replying to sender.
            # Let's extract 'From' from original
            sender = next((h["value"] for h in headers if h["name"].lower() == "from"), "")
            message['to'] = sender
            
            if msg_id_header:
                message['In-Reply-To'] = msg_id_header
                message['References'] = f"{references} {msg_id_header}".strip()

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            payload = {
                'raw': raw,
                'threadId': original.thread_id
            }
            
            response = await client.post(f"{self.GMAIL_API_URL}/messages/send", headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()

    async def forward_email(self, message_id: str, to: List[str], body: str) -> Dict[str, Any]:
        original = await self.get_email(message_id)
        if not original:
            raise ValueError(f"Email {message_id} not found")
            
        message = MIMEText(body)
        message['to'] = ", ".join(to)
        message['subject'] = f"Fwd: {original.subject}"
        
        # In a real forward, we'd attach the original content or MIME parts.
        # For now, we just send a new email with Fwd subject and body.
        # Ideally we append original snippet.
        message.set_payload(f"{body}\n\n---------- Forwarded message ---------\nFrom: {original.sender}\nDate: {original.date}\nSubject: {original.subject}\n\n{original.snippet}...")
        
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        payload = {'raw': raw}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.GMAIL_API_URL}/messages/send", headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()

    async def delete_emails(self, message_ids: List[str]) -> Dict[str, Any]:
        # Batch delete (trash)
        payload = {
            "ids": message_ids
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.GMAIL_API_URL}/messages/batchDelete", headers=self.headers, json=payload)
            response.raise_for_status()
            return {"status": "deleted", "count": len(message_ids)}

    async def modify_email_labels(self, message_id: str, add_labels: Optional[List[str]] = None, remove_labels: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Modify labels on an email.
        Common labels: UNREAD, STARRED, IMPORTANT
        """
        payload = {
            "addLabelIds": add_labels or [],
            "removeLabelIds": remove_labels or []
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.GMAIL_API_URL}/messages/{message_id}/modify",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            return {"status": "modified", "message_id": message_id}

    async def create_event(self, summary: str, start_time: datetime, end_time: datetime, attendees: List[str]) -> Dict[str, Any]:
        event = {
            'summary': summary,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'UTC', # Assuming input is UTC or offset-aware
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'UTC',
            },
            'attendees': [{'email': email} for email in attendees],
        }
        
        try:
            async with httpx.AsyncClient() as client:
                logger.info(f"Creating calendar event: {summary} from {start_time} to {end_time}")
                response = await client.post(
                    f"{self.CALENDAR_API_URL}/calendars/primary/events",
                    headers=self.headers,
                    json=event
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error creating event: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating event: {str(e)}")
            raise

    async def get_event(self, event_id: str) -> Optional[CalendarEvent]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.CALENDAR_API_URL}/calendars/primary/events/{event_id}", headers=self.headers)
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                item = response.json()
                
                start = item.get("start", {})
                end = item.get("end", {})
                start_dt = self._parse_calendar_date(start)
                end_dt = self._parse_calendar_date(end)
                
                if not start_dt or not end_dt:
                    return None

                attendees = [a.get("email") for a in item.get("attendees", []) if a.get("email")]

                return CalendarEvent(
                    id=item["id"],
                    summary=item.get("summary", "(No Title)"),
                    start=start_dt,
                    end=end_dt,
                    location=item.get("location"),
                    description=item.get("description"),
                    html_link=item.get("htmlLink"),
                    attendees=attendees
                )
        except Exception as e:
            logger.error(f"Error getting event {event_id}: {e}")
            return None

    async def update_event(self, event_id: str, **kwargs) -> Dict[str, Any]:
        patch_body = {}
        if "summary" in kwargs:
            patch_body["summary"] = kwargs["summary"]
        if "description" in kwargs:
            patch_body["description"] = kwargs["description"]
        if "location" in kwargs:
            patch_body["location"] = kwargs["location"]
        if "start_time" in kwargs:
            patch_body["start"] = {"dateTime": kwargs["start_time"].isoformat(), "timeZone": "UTC"}
        if "end_time" in kwargs:
            patch_body["end"] = {"dateTime": kwargs["end_time"].isoformat(), "timeZone": "UTC"}
        if "attendees" in kwargs:
            patch_body["attendees"] = [{"email": email} for email in kwargs["attendees"]]

        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.CALENDAR_API_URL}/calendars/primary/events/{event_id}",
                headers=self.headers,
                json=patch_body
            )
            response.raise_for_status()
            return response.json()

    async def delete_event(self, event_id: str, send_updates: bool = False) -> Dict[str, Any]:
        params = {}
        if send_updates:
            params["sendUpdates"] = "all"
            
        async with httpx.AsyncClient() as client:
            response = await client.delete(f"{self.CALENDAR_API_URL}/calendars/primary/events/{event_id}", headers=self.headers, params=params)
            if response.status_code == 204:
                return {"status": "deleted"}
            response.raise_for_status()
            return {"status": "deleted"}

    async def respond_to_invitation(self, event_id: str, response_status: str, comment: Optional[str] = None) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            # Get event
            get_resp = await client.get(f"{self.CALENDAR_API_URL}/calendars/primary/events/{event_id}", headers=self.headers)
            get_resp.raise_for_status()
            event = get_resp.json()
            
            attendees = event.get("attendees", [])
            me = next((a for a in attendees if a.get("self")), None)
            
            if not me:
                return {"status": "error", "message": "You are not an attendee of this event or cannot respond."}
            
            me["responseStatus"] = response_status
            if comment:
                me["comment"] = comment
            
            # Patch back
            patch_resp = await client.patch(
                f"{self.CALENDAR_API_URL}/calendars/primary/events/{event_id}",
                headers=self.headers,
                json={"attendees": attendees}
            )
            patch_resp.raise_for_status()
            return {"status": f"responded {response_status}"}

