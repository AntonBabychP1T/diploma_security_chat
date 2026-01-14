import httpx
import logging
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
from app.services.google_workspace import GoogleWorkspaceClient
from app.schemas.secretary import EmailMessage

logger = logging.getLogger(__name__)

class GmailSyncService:
    def __init__(self, access_token: str):
        self.client = GoogleWorkspaceClient(access_token)
        self.access_token = access_token
        self.headers = {"Authorization": f"Bearer {access_token}"}

    async def sync_incremental(self, start_history_id: int) -> Tuple[List[EmailMessage], int, bool]:
        """
        Syncs emails starting from history_id.
        Returns: (new_emails, new_history_id, history_expired)
        If history_expired is True, caller should trigger full sync.
        """
        url = f"{self.client.GMAIL_API_URL}/history"
        params = {
            "startHistoryId": str(start_history_id),
            "historyTypes": ["messageAdded"],
            # "labelId": "UNREAD" # Optional: filter changes by label? user said "new messages since last run"
        }

        try:
            async with httpx.AsyncClient() as http:
                response = await http.get(url, headers=self.headers, params=params)
                
                if response.status_code == 404:
                    # History ID not found/expired
                    logger.warning(f"History ID {start_history_id} not found/expired. Requesting full sync.")
                    return [], 0, True
                
                response.raise_for_status()
                data = response.json()
                
                history_records = data.get("history", [])
                new_history_id = int(data.get("historyId", start_history_id))
                
                added_message_ids = set()
                for record in history_records:
                    if "messagesAdded" in record:
                        for item in record["messagesAdded"]:
                            msg = item.get("message")
                            if msg:
                                added_message_ids.add(msg["id"])
                
                if not added_message_ids:
                    return [], new_history_id, False
                
                # Fetch details for added messages
                # We can reuse GoogleWorkspaceClient logic but we need to fetch specific IDs
                
                logger.info(f"Found {len(added_message_ids)} new messages via history.")
                
                # Fetch concurrent
                import asyncio
                tasks = [self.client.get_email(mid) for mid in added_message_ids]
                results = await asyncio.gather(*tasks)
                
                emails = [r for r in results if r is not None]
                return emails, new_history_id, False

        except Exception as e:
            logger.error(f"Error in incremental sync: {e}")
            raise

    async def sync_full(self, lookback_days: int = 7) -> Tuple[List[EmailMessage], int]:
        """
        Performs full sync (fallback).
        Fetches 'newer_than:Xd' (or similar filter).
        Returns: (emails, current_history_id)
        """
        # Get current history ID first to anchor future incremental syncs
        current_history_id = await self._get_current_profile_history_id()
        
        # List messages from last X days
        # We can use GoogleWorkspaceClient.list_emails but we need custom query
        # "newer_than:7d is:unread" maybe? Or just newer_than:1d for daily digest?
        # User said: "Fetch changed/new emails... list last N days, then reset stored historyId"
        
        # Let's use a specialized query
        query = f"newer_than:{lookback_days}d"
        # Optional: is:unread? If we want digest of unread only. User: "checks Gmail for new messages"
        # Let's assume user wants to see what arrived.
        
        # Construct ad-hoc query
        try:
            params = {"q": query} # defaults maxResults=100 in list_emails? No, we should call API directly here for control
            
            # Using client.list_emails would be easier if it supports custom Q
            # client.list_emails accepts EmailFilters. Let's look at it.
            # filters.subject_keyword etc.
            # It joins query parts.
            
            # Let's manually call list messages to ensure we get what we want
            url = f"{self.client.GMAIL_API_URL}/messages"
            
            async with httpx.AsyncClient() as http:
                # 1. Get messages
                # Fetch more than default 10? Maybe 50.
                params = {"q": query, "maxResults": 50}
                resp = await http.get(url, headers=self.headers, params=params)
                resp.raise_for_status()
                data = resp.json()
                
                messages_meta = data.get("messages", [])
                
                import asyncio
                tasks = [self.client.get_email(m["id"]) for m in messages_meta]
                results = await asyncio.gather(*tasks)
                
                emails = [r for r in results if r is not None]
                
                return emails, current_history_id

        except Exception as e:
            logger.error(f"Error in full sync: {e}")
            raise

    async def _get_current_profile_history_id(self) -> int:
        async with httpx.AsyncClient() as http:
            resp = await http.get(f"{self.client.GMAIL_API_URL}/profile", headers=self.headers)
            resp.raise_for_status()
            data = resp.json()
            return int(data.get("historyId", 0))

    async def get_raw_message_headers(self, message_id: str) -> Dict[str, str]:
        """Helper to get raw headers for precise threading/replying if needed later"""
        url = f"{self.client.GMAIL_API_URL}/messages/{message_id}?format=metadata"
        async with httpx.AsyncClient() as http:
            resp = await http.get(url, headers=self.headers)
            if resp.status_code == 200:
                payload = resp.json().get("payload", {})
                headers_list = payload.get("headers", [])
                return {h["name"]: h["value"] for h in headers_list}
        return {}
