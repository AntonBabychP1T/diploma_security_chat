import httpx
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from app.schemas.secretary import EmailMessage, CalendarEvent, TimeSlot, EmailFilters

class MicrosoftGraphClient:
    GRAPH_API_URL = "https://graph.microsoft.com/v1.0"

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Prefer": "outlook.timezone=\"UTC\"" # Ensure UTC
        }

    async def list_emails(self, filters: Optional[EmailFilters] = None) -> List[EmailMessage]:
        query_params = {
            "$top": 10,
            "$select": "id,subject,from,bodyPreview,receivedDateTime,isRead,webLink,conversationId"
        }
        
        filter_clauses = []
        if filters:
            if filters.max_results:
                query_params["$top"] = filters.max_results
            
            if filters.is_unread:
                filter_clauses.append("isRead eq false")
            
            if filters.sender:
                # OData filter for sender
                filter_clauses.append(f"from/emailAddress/address eq '{filters.sender}'")
            
            if filters.subject_keyword:
                # $search is better for keywords but requires consistency. 
                # $filter contains is safer for simple usage if $search not enabled/supported fully on all endpoints
                filter_clauses.append(f"contains(subject, '{filters.subject_keyword}')")

        if filter_clauses:
            query_params["$filter"] = " and ".join(filter_clauses)

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.GRAPH_API_URL}/me/messages", headers=self.headers, params=query_params)
            response.raise_for_status()
            data = response.json()
            items = data.get("value", [])
            
            results = []
            for item in items:
                results.append(self._parse_email(item))
            return results

    def _parse_email(self, data: Dict[str, Any]) -> EmailMessage:
        sender_data = data.get("from", {}).get("emailAddress", {})
        sender_name = sender_data.get("name", "")
        sender_address = sender_data.get("address", "")
        sender = f"{sender_name} <{sender_address}>" if sender_name else sender_address
        
        return EmailMessage(
            id=data["id"],
            thread_id=data.get("conversationId", ""),
            subject=data.get("subject", "(No Subject)"),
            sender=sender,
            snippet=data.get("bodyPreview", ""),
            date=datetime.fromisoformat(data["receivedDateTime"].replace("Z", "+00:00")),
            is_read=data.get("isRead", True),
            link=data.get("webLink")
        )

    async def list_events(self, time_min: datetime, time_max: datetime) -> List[CalendarEvent]:
        params = {
            "startDateTime": time_min.isoformat() + "Z",
            "endDateTime": time_max.isoformat() + "Z",
            "$select": "id,subject,start,end,location,bodyPreview,webLink,attendees",
            "$orderby": "start/dateTime"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.GRAPH_API_URL}/me/calendarView", headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            items = data.get("value", [])
            
            events = []
            for item in items:
                events.append(self._parse_event(item))
            return events

    def _parse_event(self, item: Dict[str, Any]) -> CalendarEvent:
        start = item.get("start", {})
        end = item.get("end", {})
        
        # Graph API returns time in UTC if Prefer header is set
        start_dt = datetime.fromisoformat(start["dateTime"].replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end["dateTime"].replace("Z", "+00:00"))
        
        attendees = [
            a.get("emailAddress", {}).get("address") 
            for a in item.get("attendees", []) 
            if a.get("emailAddress", {}).get("address")
        ]

        return CalendarEvent(
            id=item["id"],
            summary=item.get("subject", "(No Title)"),
            start=start_dt,
            end=end_dt,
            location=item.get("location", {}).get("displayName"),
            description=item.get("bodyPreview"),
            html_link=item.get("webLink"),
            attendees=attendees
        )

    async def find_free_slots(self, time_min: datetime, time_max: datetime, duration_minutes: int = 30) -> List[TimeSlot]:
        # Reuse logic: Get all events, find gaps
        events = await self.list_events(time_min, time_max)
        
        slots = []
        current_time = time_min
        
        # Events are already sorted by start time from API
        
        for event in events:
            # Check gap
            if event.start > current_time:
                gap = event.start - current_time
                if gap >= timedelta(minutes=duration_minutes):
                    slots.append(TimeSlot(
                        start=current_time,
                        end=event.start,
                        duration_minutes=int(gap.total_seconds() / 60)
                    ))
            
            if event.end > current_time:
                current_time = event.end
        
        if time_max > current_time:
            gap = time_max - current_time
            if gap >= timedelta(minutes=duration_minutes):
                slots.append(TimeSlot(
                    start=current_time,
                    end=time_max,
                    duration_minutes=int(gap.total_seconds() / 60)
                ))
                
    async def get_email(self, message_id: str) -> Optional[EmailMessage]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.GRAPH_API_URL}/me/messages/{message_id}", headers=self.headers)
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                return self._parse_email(response.json())
        except Exception as e:
            # logger.error(f"Error getting email {message_id}: {e}") # Logger not imported in this file?
            return None

    async def reply_email(self, message_id: str, body: str, reply_all: bool = False) -> Dict[str, Any]:
        endpoint = "replyAll" if reply_all else "reply"
        payload = {
            "comment": body
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.GRAPH_API_URL}/me/messages/{message_id}/{endpoint}", headers=self.headers, json=payload)
            response.raise_for_status()
            return {"status": "sent"}

    async def forward_email(self, message_id: str, to: List[str], body: str) -> Dict[str, Any]:
        payload = {
            "comment": body,
            "toRecipients": [
                {"emailAddress": {"address": email}} for email in to
            ]
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.GRAPH_API_URL}/me/messages/{message_id}/forward", headers=self.headers, json=payload)
            response.raise_for_status()
            return {"status": "sent"}

    async def delete_emails(self, message_ids: List[str], hard_delete: bool = False) -> Dict[str, Any]:
        # Simple loop for now
        count = 0
        async with httpx.AsyncClient() as client:
            for mid in message_ids:
                # Move to deleted items usually, but DELETE operation does that in Exchange/Graph usually (soft delete)
                # If hard_delete, we might need to purge, but for now just delete.
                response = await client.delete(f"{self.GRAPH_API_URL}/me/messages/{mid}", headers=self.headers)
                if response.status_code == 204:
                    count += 1
        return {"status": "deleted", "count": count}

    async def modify_email_labels(self, message_id: str, add_labels: Optional[List[str]] = None, remove_labels: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Modify email properties in Microsoft Graph.
        Maps Gmail labels to Graph properties:
        - UNREAD -> isRead: false
        - (remove) UNREAD -> isRead: true
        - STARRED -> flag: flagged
        - (remove) STARRED -> flag: notFlagged
        """
        payload = {}
        
        if add_labels:
            if "UNREAD" in add_labels:
                payload["isRead"] = False
            if "STARRED" in add_labels:
                payload["flag"] = {"flagStatus": "flagged"}
        
        if remove_labels:
            if "UNREAD" in remove_labels:
                payload["isRead"] = True
            if "STARRED" in remove_labels:
                payload["flag"] = {"flagStatus": "notFlagged"}
        
        if not payload:
            return {"status": "no_changes", "message_id": message_id}
        
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.GRAPH_API_URL}/me/messages/{message_id}",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            return {"status": "modified", "message_id": message_id}

    async def get_event(self, event_id: str) -> Optional[CalendarEvent]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.GRAPH_API_URL}/me/events/{event_id}", headers=self.headers)
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                return self._parse_event(response.json())
        except Exception as e:
            return None

    async def update_event(self, event_id: str, **kwargs) -> Dict[str, Any]:
        patch_body = {}
        if "summary" in kwargs:
            patch_body["subject"] = kwargs["summary"]
        if "description" in kwargs:
            patch_body["body"] = {"contentType": "Text", "content": kwargs["description"]}
        if "location" in kwargs:
            patch_body["location"] = {"displayName": kwargs["location"]}
        if "start_time" in kwargs:
            patch_body["start"] = {"dateTime": kwargs["start_time"].isoformat(), "timeZone": "UTC"}
        if "end_time" in kwargs:
            patch_body["end"] = {"dateTime": kwargs["end_time"].isoformat(), "timeZone": "UTC"}
        if "attendees" in kwargs:
            patch_body["attendees"] = [
                {
                    "emailAddress": {"address": email},
                    "type": "required"
                } for email in kwargs["attendees"]
            ]

        async with httpx.AsyncClient() as client:
            response = await client.patch(f"{self.GRAPH_API_URL}/me/events/{event_id}", headers=self.headers, json=patch_body)
            response.raise_for_status()
            return response.json()

    async def delete_event(self, event_id: str, send_updates: bool = False) -> Dict[str, Any]:
        # send_updates logic for Graph? 
        # Graph API doesn't have sendUpdates param for DELETE event directly in query params usually?
        # Actually it does not seem to support it in the same way as Google.
        # But we accept the arg to match interface.
        async with httpx.AsyncClient() as client:
            response = await client.delete(f"{self.GRAPH_API_URL}/me/events/{event_id}", headers=self.headers)
            if response.status_code == 204:
                return {"status": "deleted"}
            response.raise_for_status()
            return {"status": "deleted"}

    async def respond_to_invitation(self, event_id: str, response_status: str, comment: Optional[str] = None) -> Dict[str, Any]:
        # response_status: "accepted", "declined", "tentative"
        endpoint_map = {
            "accepted": "accept",
            "declined": "decline",
            "tentative": "tentativelyAccept"
        }
        endpoint = endpoint_map.get(response_status.lower())
        if not endpoint:
            raise ValueError(f"Invalid response status: {response_status}")
            
        payload = {}
        if comment:
            payload["comment"] = comment

        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.GRAPH_API_URL}/me/events/{event_id}/{endpoint}", headers=self.headers, json=payload)
            if response.status_code == 202:
                return {"status": f"responded {response_status}"}
            response.raise_for_status()
            return {"status": f"responded {response_status}"}

    async def send_email(self, to: List[str], subject: str, body: str) -> Dict[str, Any]:
        message = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "Text",
                    "content": body
                },
                "toRecipients": [
                    {"emailAddress": {"address": email}} for email in to
                ]
            },
            "saveToSentItems": "true"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.GRAPH_API_URL}/me/sendMail", headers=self.headers, json=message)
            if response.status_code == 202:
                return {"status": "sent"}
            response.raise_for_status()
            return response.json()

    async def create_event(self, summary: str, start_time: datetime, end_time: datetime, attendees: List[str]) -> Dict[str, Any]:
        event = {
            "subject": summary,
            "start": {
                "dateTime": start_time.isoformat(),
                "timeZone": "UTC"
            },
            "end": {
                "dateTime": end_time.isoformat(),
                "timeZone": "UTC"
            },
            "attendees": [
                {
                    "emailAddress": {
                        "address": email,
                        "name": email
                    },
                    "type": "required"
                } for email in attendees
            ]
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.GRAPH_API_URL}/me/events", headers=self.headers, json=event)
            response.raise_for_status()
            return response.json()
