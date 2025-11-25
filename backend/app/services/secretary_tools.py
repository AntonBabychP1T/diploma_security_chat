from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from app.models.google_account import GoogleAccount
from app.services.google_workspace import GoogleWorkspaceClient
from app.services.google_auth_service import GoogleAuthService
from app.schemas.secretary import EmailFilters, EmailMessage, CalendarEvent, TimeSlot

logger = logging.getLogger(__name__)

class SecretaryTools:
    def __init__(self, db: AsyncSession, user_id: int):
        self.db = db
        self.user_id = user_id

    async def list_emails(self, account_label: str, filters: Dict[str, Any]) -> str:
        """
        Lists emails based on filters.
        """
        client = await self._get_client(account_label)
        if not client:
            return f"Error: Could not access account with label '{account_label}'."

        email_filters = EmailFilters(**filters)
        try:
            emails = await client.list_emails(email_filters)
            if not emails:
                return "No emails found matching the criteria."
            
            # Format for LLM
            lines = [f"Found {len(emails)} emails:"]
            for e in emails[:10]: # Limit to 10 for context window
                lines.append(f"- [{e.date.strftime('%Y-%m-%d %H:%M')}] From: {e.sender} | Subject: {e.subject} | Snippet: {e.snippet}")
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Error listing emails: {e}")
            return f"Error listing emails: {str(e)}"

    async def list_events(self, account_label: str, start_time: str, end_time: str) -> str:
        """
        Lists calendar events.
        """
        client = await self._get_client(account_label)
        if not client:
            return f"Error: Could not access account with label '{account_label}'."

        try:
            start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            
            events = await client.list_events(start, end)
            if not events:
                return "No events found in this time range."
            
            lines = [f"Found {len(events)} events:"]
            for ev in events:
                lines.append(f"- {ev.start.strftime('%Y-%m-%d %H:%M')} - {ev.end.strftime('%H:%M')} | {ev.summary}")
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Error listing events: {e}")
            return f"Error listing events: {str(e)}"

    async def find_free_slots(self, account_label: str, start_time: str, end_time: str, duration_minutes: int) -> str:
        """
        Finds free slots.
        """
        client = await self._get_client(account_label)
        if not client:
            return f"Error: Could not access account with label '{account_label}'."

        try:
            start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            
            slots = await client.find_free_slots(start, end, duration_minutes)
            if not slots:
                return "No free slots found."
            
            lines = [f"Found {len(slots)} free slots:"]
            for s in slots[:10]:
                lines.append(f"- {s.start.strftime('%Y-%m-%d %H:%M')} ({s.duration_minutes} min)")
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Error finding slots: {e}")
            return f"Error finding slots: {str(e)}"

    async def _get_client(self, label: str) -> Optional[GoogleWorkspaceClient]:
        # Resolve account
        query = select(GoogleAccount).where(GoogleAccount.user_id == self.user_id)
        result = await self.db.execute(query)
        accounts = result.scalars().all()
        
        target_account = None
        if not label or label.lower() == "all":
            # Default to first or specific logic? For now, pick first or 'work' if exists
            target_account = next((a for a in accounts if a.label == "work"), accounts[0] if accounts else None)
        else:
            target_account = next((a for a in accounts if a.label.lower() == label.lower()), None)
            
        # Fallback: If 'work' was requested (default) but not found, and we have accounts, use the first one.
        if not target_account and label == "work" and accounts:
            target_account = accounts[0]
            
        if not target_account:
            return None

        # Check expiry
        if target_account.token_expiry and target_account.token_expiry < datetime.utcnow() + timedelta(minutes=5):
            if not target_account.refresh_token:
                return None
            try:
                new_tokens = await GoogleAuthService.refresh_access_token(target_account.refresh_token)
                target_account.access_token = new_tokens["access_token"]
                target_account.token_expiry = datetime.utcnow() + timedelta(seconds=new_tokens.get("expires_in", 3600))
                await self.db.commit()
            except Exception as e:
                logger.error(f"Failed to refresh token: {e}")
                return None
        
        return GoogleWorkspaceClient(target_account.access_token)
