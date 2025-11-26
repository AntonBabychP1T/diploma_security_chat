from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from app.models.google_account import GoogleAccount
from app.models.microsoft_account import MicrosoftAccount
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

    async def send_email(self, account_label: str, to: List[str], subject: str, body: str) -> str:
        """
        Sends an email.
        """
        client = await self._get_client(account_label)
        if not client:
            return f"Error: Could not access account with label '{account_label}'."

        try:
            await client.send_email(to, subject, body)
            return f"Email sent to {', '.join(to)} with subject '{subject}'."
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return f"Error sending email: {str(e)}"

    async def create_event(self, account_label: str, summary: str, start_time: str, end_time: str, attendees: List[str]) -> str:
        """
        Creates a calendar event.
        """
        client = await self._get_client(account_label)
        if not client:
            return f"Error: Could not access account with label '{account_label}'."

        try:
            start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            
            await client.create_event(summary, start, end, attendees)
            return f"Event '{summary}' created from {start_time} to {end_time} with attendees {', '.join(attendees)}."
        except Exception as e:
            logger.error(f"Error creating event: {e}")
            return f"Error creating event: {str(e)}"

    async def _get_client(self, label: str) -> Optional[Any]: # Returns MailCalendarProvider
        # 1. Try Google Accounts
        query = select(GoogleAccount).where(GoogleAccount.user_id == self.user_id)
        result = await self.db.execute(query)
        google_accounts = result.scalars().all()
        
        # 2. Try Microsoft Accounts
        query_ms = select(MicrosoftAccount).where(MicrosoftAccount.user_id == self.user_id)
        result_ms = await self.db.execute(query_ms)
        ms_accounts = result_ms.scalars().all()
        
        all_accounts = []
        for acc in google_accounts:
            all_accounts.append({"type": "google", "account": acc})
        for acc in ms_accounts:
            all_accounts.append({"type": "microsoft", "account": acc})
            
        target = None
        if not label or label.lower() == "all":
            # Default to work, then first available
            target = next((a for a in all_accounts if a["account"].label == "work"), all_accounts[0] if all_accounts else None)
        else:
            target = next((a for a in all_accounts if a["account"].label.lower() == label.lower()), None)
            
        if not target:
            # Fallback if specific label not found but 'work' was requested (default)
            if label == "work" and all_accounts:
                target = all_accounts[0]
        
        if not target:
            return None
            
        account = target["account"]
        account_type = target["type"]
        
        # Check expiry and refresh
        if account.token_expiry and account.token_expiry < datetime.utcnow() + timedelta(minutes=5):
            if not account.refresh_token:
                return None
            try:
                if account_type == "google":
                    new_tokens = await GoogleAuthService.refresh_access_token(account.refresh_token)
                    account.access_token = new_tokens["access_token"]
                    account.token_expiry = datetime.utcnow() + timedelta(seconds=new_tokens.get("expires_in", 3600))
                elif account_type == "microsoft":
                    from app.services.microsoft_auth_service import MicrosoftAuthService
                    new_tokens = await MicrosoftAuthService.refresh_access_token(account.refresh_token)
                    account.access_token = new_tokens["access_token"]
                    account.token_expiry = datetime.utcnow() + timedelta(seconds=new_tokens.get("expires_in", 3600))
                    if "refresh_token" in new_tokens:
                        account.refresh_token = new_tokens["refresh_token"]
                
                await self.db.commit()
            except Exception as e:
                logger.error(f"Failed to refresh token for {account_type} account {account.id}: {e}")
                return None

        if account_type == "google":
            return GoogleWorkspaceClient(account.access_token)
        elif account_type == "microsoft":
            from app.services.microsoft_graph import MicrosoftGraphClient
            return MicrosoftGraphClient(account.access_token)
            
        return None
