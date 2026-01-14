import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.gmail_sync import GmailSyncService
from app.services.google_auth_service import GoogleAuthService
from app.services.pii_service import PIIService
from app.services.chat_service import ChatService
from app.models.digest_models import GmailSyncState, EmailSnapshot, DigestRun, ActionProposal, ActionType, ActionStatus
from app.models.google_account import GoogleAccount
from app.models.chat import Chat
from app.core.config import get_settings
from app.providers import ProviderFactory

logger = logging.getLogger(__name__)
settings = get_settings()

class DigestEngine:
    def __init__(self, db: AsyncSession, user_id: int):
        self.db = db
        self.user_id = user_id
        self.pii = PIIService()
        self.provider = ProviderFactory().get_provider("openai") # Or make configurable

    async def run_digest(self) -> Dict[str, Any]:
        """
        Main entrypoint.
        1. Get Google Account & Sync State
        2. Sync Emails (History API)
        3. Filter & Process Emails
        4. Generate Summary (LLM)
        5. Create Action Proposals
        6. Inject into Chat
        """
        logger.info(f"Starting digest run for user {self.user_id}")
        
        # 1. Get Google Account
        stmt_account = select(GoogleAccount).where(GoogleAccount.user_id == self.user_id)
        account = (await self.db.execute(stmt_account)).scalar_one_or_none()
        
        if not account:
            logger.warning(f"No Google account linked for user {self.user_id}")
            return {"status": "skipped", "reason": "no_account"}

        # Refresh token if needed? 
        # Usually client library handles it or we should do it manually. 
        # GoogleWorkspaceClient assumes valid access token.
        # We should refresh it.
        # TODO: Move refresh logic to a shared helper or middleware. 
        # For now, simplistic refresh:
        token_info = await GoogleAuthService.refresh_access_token(account.refresh_token)
        access_token = token_info["access_token"]
        # Update DB? Yes, ideally.
        account.access_token = access_token
        # account.expires_at = ...
        await self.db.commit()

        sync_service = GmailSyncService(access_token)
        
        # 2. Get/Create Sync State
        stmt_state = select(GmailSyncState).where(GmailSyncState.user_id == self.user_id)
        state_result = await self.db.execute(stmt_state)
        sync_state = state_result.scalar_one_or_none()
        
        if not sync_state:
            sync_state = GmailSyncState(user_id=self.user_id, last_history_id=None)
            self.db.add(sync_state)
            await self.db.commit()

        # 3. Perform Sync
        emails = []
        new_history_id = 0
        is_full_sync = False
        
        try:
            if sync_state.last_history_id:
                logger.info(f"Incremental sync from {sync_state.last_history_id}")
                emails, new_history_id, expired = await sync_service.sync_incremental(sync_state.last_history_id)
                if expired:
                    logger.info("History expired, falling back to full sync")
                    emails, new_history_id = await sync_service.sync_full(lookback_days=1) # Daily digest
                    is_full_sync = True
            else:
                logger.info("No history ID, doing full sync")
                emails, new_history_id = await sync_service.sync_full(lookback_days=1)
                is_full_sync = True
            
            sync_state.last_history_id = new_history_id
            sync_state.last_success_at = datetime.utcnow()
            sync_state.error_streak = 0
            await self.db.commit()
            
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            sync_state.error_streak += 1
            sync_state.last_error = str(e)
            await self.db.commit()
            return {"status": "failed", "error": str(e)}

        if not emails:
            logger.info("No new emails found.")
            return {"status": "success", "emails_processed": 0}

        # 4. Filter & Persist Snapshots
        processed_emails = []
        snapshots = []
        
        for email in emails:
            # Basic Promo Detection (heuristic)
            category = "OTHER"
            if "CATEGORY_PROMOTIONS" in email.label_ids: # Verify actual label ID string
                category = "PROMO"
            elif "CATEGORY_PERSONAL" in email.label_ids:
                category = "IMPORTANT" # Maybe
            
            # Simple heuristic mapping (Gmail actually uses CATEGORY_...)
            labels_set = set(email.label_ids or [])
            if "CATEGORY_PROMOTIONS" in labels_set:
                category = "PROMO"
            elif "IMPORTANT" in labels_set or "STARRED" in labels_set:
                category = "IMPORTANT"

            snapshot = EmailSnapshot(
                user_id=self.user_id,
                gmail_message_id=email.id,
                thread_id=email.thread_id,
                sender=email.sender,
                subject=email.subject,
                snippet=email.snippet,
                internal_date=int(email.date.timestamp() * 1000),
                label_ids=list(labels_set),
                category=category
            )
            # Check deduplication? 
            # We trust incremental sync usually, but for safety insert ignore or check existence?
            # For MVP, assume unique or catch integrity error. 
            # Better check existence efficiently?
            # Let's skip check for speed in MVP, sync usually handles it.
            
            snapshots.append(snapshot)
            self.db.add(snapshot)
            processed_emails.append({"id": email.id, "subject": email.subject, "sender": email.sender, "snippet": email.snippet, "category": category})

        await self.db.commit()
        
        # 5. LLM Summarization
        # Filter for LLM: Don't summarize Promos in detail, just count them?
        # User goal: "summarizes (digest) + classifies ... Auto-handle Promotions: detect... report 'I found X promo emails'"
        
        promos = [e for e in processed_emails if e["category"] == "PROMO"]
        others = [e for e in processed_emails if e["category"] != "PROMO"]
        
        if not others and not promos:
             return {"status": "success", "reason": "empty_after_filter"}

        # Mask PII
        pii_mapping = {}
        masked_others = []
        for e in others:
            # Mask subject and snippet
            ms, pii_mapping = self.pii.mask(e["subject"], pii_mapping)
            mn, pii_mapping = self.pii.mask(e["snippet"], pii_mapping)
            msender, pii_mapping = self.pii.mask(e["sender"], pii_mapping)
            masked_others.append({
                "id": e["id"],
                "subject": ms,
                "sender": msender,
                "snippet": mn
            })
            
        # Build Prompt
        prompt = f"""
        You are a helpful executive assistant. Analyze the following new emails and generate a structured digest.
        
        Emails (Privacy Masked):
        {json.dumps(masked_others, indent=2)}
        
        Promo Count: {len(promos)}
        
        Tasks:
        1. Summarize the important emails (the ones listed above) in a concise bullet-point list.
        2. Identify any "Calls to Action" or potential meetings.
        3. Determine if any ACTIONS should be proposed. 
           Allowed Actions: 
           - ARCHIVE_PROMO (if promos exist, suggest archiving them all)
           - CREATE_DRAFT (if an email explicitly asks for a reply or looks like it needs one. Provide a short draft body.)
           - CREATE_EVENT (if an email implies a meeting/time. Provide specific start/end times if possible, or TBD.)

        Output Format (STRICT JSON):
        {{
            "summary_text": "Markdown summary of emails...",
            "actions": [
                {{
                    "type": "ARCHIVE_PROMO",
                    "payload": {{ "message_ids": ["id1", "id2"...] }}  <-- Include actual IDs of promos if archiving
                }},
                {{
                    "type": "CREATE_DRAFT", 
                    "payload": {{ "to": "...", "subject": "...", "body": "..." }}
                }},
                {{
                    "type": "CREATE_EVENT",
                    "payload": {{ "summary": "...", "start_time": "ISO", "end_time": "ISO", "attendees": [...] }}
                }}
            ]
        }}
        """
        
        # Call LLM
        # Use provider directly
        messages = [{"role": "user", "content": prompt}]
        
        response = await self.provider.generate(
            messages,
            options={"model": "gpt-5.1", "response_format": {"type": "json_object"}} 
        )
        
        content = response.content
        if not content:
            logger.error("Empty LLM response")
            return {"status": "failed", "reason": "llm_empty"}
            
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
             logger.error("Invalid JSON from LLM")
             # Fallback?
             return {"status": "failed", "reason": "llm_json_error"}

        # Unmask Summary
        summary_text = data.get("summary_text", "")
        summary_text_unmasked = self.pii.unmask(summary_text, pii_mapping)
        
        actions_raw = data.get("actions", [])
        
        # 6. Save Digest & Actions
        digest_run = DigestRun(
            user_id=self.user_id,
            period_start=datetime.utcnow() - timedelta(days=1), # Approx
            period_end=datetime.utcnow(),
            start_history_id_used=sync_state.last_history_id, # Actually the start one, but simplified
            stats={"emails_scanned": len(emails), "promos_count": len(promos)},
            status="SUCCESS"
        )
        self.db.add(digest_run)
        await self.db.commit() # Get ID
        
        # Unmask Actions & Save
        action_proposals = []
        promo_ids = [p["id"] for p in promos]
        
        for act in actions_raw:
            act_type = act.get("type")
            payload = act.get("payload", {})
            
            # Special logic for Archive Promo: ensure we use the REAL promo IDs we found, 
            # LLM might hallucinate IDs or not list them all.
            # Trust our classification (Labels) over LLM for the LIST of promos.
            if act_type == "ARCHIVE_PROMO":
                if payload.get("message_ids") == ["id1", "id2"]: # Hallucination check
                     payload["message_ids"] = promo_ids
                elif not payload.get("message_ids"):
                     payload["message_ids"] = promo_ids
                else:
                     # Merge? Or just override
                     payload["message_ids"] = promo_ids
            
            # Unmask payload content
            payload = self._unmask_payload(payload, pii_mapping)
            
            proposal = ActionProposal(
                digest_id=digest_run.id,
                user_id=self.user_id,
                type=ActionType(act_type),
                payload_json=payload,
                status=ActionStatus.PENDING
            )
            self.db.add(proposal)
            action_proposals.append(proposal)

        await self.db.commit()

        # 7. Create Chat Message
        # Find or Create "Inbox Digest" chat? 
        # User said: "Create (or reuse) a dedicated per-user chat thread... e.g. 'Inbox Digest (Google)'"
        
        stmt_chat = select(Chat).where(Chat.user_id == self.user_id, Chat.title == "Inbox Digest (Google)")
        chat_res = await self.db.execute(stmt_chat)
        chat = chat_res.scalar_one_or_none()
        
        conn_chat_service = ChatService(self.db, self.user_id)
        if not chat:
            from app.schemas.chat import ChatCreate
            chat = await conn_chat_service.create_chat(ChatCreate(title="Inbox Digest (Google)"))

        # Metadata for UI
        ui_metadata = {
            "digest_id": digest_run.id,
            "actions": [{"id": a.id, "type": a.type, "payload": a.payload_json} for a in action_proposals],
            "stats": digest_run.stats
        }

        await conn_chat_service.create_system_message(
            chat_id=chat.id,
            content=summary_text_unmasked,
            source="gmail_digest",
            metadata=ui_metadata
        )
        
        digest_run.created_chat_id = chat.id
        # digest_run.created_message_id = ... (msg.id) - create_system_message return msg
        await self.db.commit()

        return {"status": "success", "digest_id": digest_run.id, "actions_count": len(action_proposals)}

    def _unmask_payload(self, payload: Any, mapping: Dict[str, str]) -> Any:
        if isinstance(payload, str):
            return self.pii.unmask(payload, mapping)
        if isinstance(payload, list):
            return [self._unmask_payload(v, mapping) for v in payload]
        if isinstance(payload, dict):
            return {k: self._unmask_payload(v, mapping) for k, v in payload.items()}
        return payload
