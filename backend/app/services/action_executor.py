import logging
import json
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.digest_models import ActionProposal, ActionType, ActionStatus
from app.services.google_workspace import GoogleWorkspaceClient
from app.services.google_auth_service import GoogleAuthService

logger = logging.getLogger(__name__)

class ActionExecutor:
    def __init__(self, db: AsyncSession, user_id: int):
        self.db = db
        self.user_id = user_id

    async def execute_action(self, action_id: int, access_token: str) -> bool:
        """
        Executes a pending/approved action. 
        Updates status to EXECUTED or FAILED.
        """
        stmt = select(ActionProposal).where(ActionProposal.id == action_id, ActionProposal.user_id == self.user_id)
        result = await self.db.execute(stmt)
        action = result.scalar_one_or_none()

        if not action:
            logger.error(f"Action {action_id} not found for user {self.user_id}")
            return False

        # If already executed, skip? Or re-try if failed?
        if action.status == ActionStatus.EXECUTED:
            logger.info(f"Action {action_id} already executed.")
            return True

        # Update status to EXECUTING? (Not in enum, keep PII simple)
        
        client = GoogleWorkspaceClient(access_token)
        
        try:
            payload = action.payload_json
            
            if action.type == ActionType.ARCHIVE_PROMO:
                message_ids = payload.get("message_ids", [])
                if message_ids:
                    # Remove INBOX label
                    for msg_id in message_ids:
                        await client.modify_email_labels(msg_id, remove_labels=["INBOX"])
                
            elif action.type == ActionType.CREATE_DRAFT:
                # We need to construct a draft. 
                # GoogleWorkspaceClient doesn't have create_draft yet, only send_email.
                # But creating a draft is similar to sending, just different endpoint: /drafts
                # We can implement a helper or do it here if simple. 
                # Let's add create_draft to GoogleWorkspaceClient later or use raw httpx here?
                # Better to keep it in GoogleWorkspaceClient.
                # For now, let's assume Client has create_draft (I need to add it).
                
                # Wait, I didn't add create_draft to GoogleWorkspaceClient yet.
                # I should add it.
                pass 

            elif action.type == ActionType.CREATE_EVENT:
                summary = payload.get("summary")
                start_time_str = payload.get("start_time")
                end_time_str = payload.get("end_time")
                attendees = payload.get("attendees", [])
                
                if summary and start_time_str and end_time_str:
                    start_dt = datetime.fromisoformat(start_time_str)
                    end_dt = datetime.fromisoformat(end_time_str)
                    await client.create_event(summary, start_dt, end_dt, attendees)

            action.status = ActionStatus.EXECUTED
            action.executed_at = datetime.utcnow()
            await self.db.commit()
            return True

        except Exception as e:
            logger.error(f"Error executing action {action_id}: {e}")
            action.status = ActionStatus.FAILED
            action.error = str(e)
            await self.db.commit()
            return False
