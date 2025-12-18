from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import json
import logging
from datetime import datetime, timedelta

from app.models.google_account import GoogleAccount
from app.services.google_workspace import GoogleWorkspaceClient
from app.services.google_auth_service import GoogleAuthService
from app.providers import ProviderFactory
from app.core.config import get_settings
from app.services.secretary_tools import SecretaryTools
from app.services.pii_service import PIIService
from app.services.tools_definition import SECRETARY_TOOLS_DEFINITION
from typing import Dict, List, Any

logger = logging.getLogger(__name__)
settings = get_settings()

class SecretaryService:
    def __init__(self, db: AsyncSession, user_id: int):
        self.db = db
        self.user_id = user_id
        self.provider = ProviderFactory.get_provider("openai")
        self.tools_impl = SecretaryTools(db, user_id)
        self.pii = PIIService()

    async def process_request(self, query: str, history: Optional[List[dict]] = None) -> str:
        # PII Mapping
        pii_mapping: Dict[str, str] = {}
        
        # Mask History
        masked_history = []
        if history:
            for msg in history[-8:]:
                if "content" in msg and isinstance(msg["content"], str):
                    masked_content, pii_mapping = self.pii.mask(msg["content"], mapping=pii_mapping)
                    new_msg = {**msg, "content": masked_content}
                    masked_history.append(new_msg)
                else:
                    masked_history.append(msg)
        
        # Mask Query
        masked_query, pii_mapping = self.pii.mask(query, mapping=pii_mapping)
        
        # 1. Define Tools
        tools = SECRETARY_TOOLS_DEFINITION

        # 2. Prepare Messages
        current_time = datetime.utcnow().isoformat()
        system_prompt = f"""You are a helpful mail and calendar secretary agent.
Current time (UTC): {current_time}
You have access to tools to read emails and calendars, find slots, and create/update/delete events.
Use the tools directly without asking for extra confirmation unless the user is ambiguous.
If the user asks for "today", "tomorrow", etc., calculate the ISO dates based on the Current time.
When asked to "move" an event, prefer using `update_event` to change its time if you can find the event ID.

IMPORTANT:
- Keep max_results low (5-10) unless the user specifically asks for more emails.
- Don't repeat the same tool call multiple times.
- Use list_events with specific date ranges, not broad multi-day queries unless necessary.

Be concise: respond in 1-3 short sentences summarizing the tool results.
"""
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(masked_history)
        messages.append({"role": "user", "content": masked_query})

        # 3. Agent Loop
        max_turns = getattr(settings, "SECRETARY_MAX_TURNS", 5)
        import asyncio
        for _ in range(max_turns):
            response = await self.provider.generate(
                messages,
                options={"tools": tools, "tool_choice": "auto"}
            )
            
            message_content = response.content
            tool_calls = response.tool_calls

            # Add assistant message to history
            assistant_msg = {"role": "assistant"}
            if message_content:
                assistant_msg["content"] = message_content
            if tool_calls:
                assistant_msg["tool_calls"] = tool_calls 
            
            messages.append(assistant_msg)

            if not tool_calls:
                # Final response
                if message_content:
                    return self.pii.unmask(message_content, pii_mapping)
                return "I'm done."

            # Execute Tools in Parallel
            tasks = []
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                call_id = tool_call.id
                
                # Unmask arguments
                unmasked_args = self._unmask_structure(arguments, pii_mapping)

                logger.info(f"Executing tool {function_name} with args {unmasked_args}")
                
                async def execute_tool(fname, args, cid):
                    try:
                        if fname == "list_emails":
                            res = await self.tools_impl.list_emails(args.get("account_label", "work"), args.get("filters", {}))
                        elif fname == "list_events":
                            res = await self.tools_impl.list_events(args.get("account_label", "work"), args.get("start_time"), args.get("end_time"))
                        elif fname == "find_free_slots":
                            res = await self.tools_impl.find_free_slots(args.get("account_label", "work"), args.get("start_time"), args.get("end_time"), args.get("duration_minutes"))
                        elif fname == "create_event":
                            res = await self.tools_impl.create_event(args.get("account_label", "work"), args.get("summary", "Untitled"), args.get("start_time"), args.get("end_time"), args.get("attendees", []) or [])
                        elif fname == "reply_email":
                            res = await self.tools_impl.reply_email(args.get("account_label", "work"), args.get("message_id"), args.get("body"), args.get("reply_all", False))
                        elif fname == "forward_email":
                            res = await self.tools_impl.forward_email(args.get("account_label", "work"), args.get("message_id"), args.get("to"), args.get("body"))
                        elif fname == "delete_emails":
                            res = await self.tools_impl.delete_emails(args.get("account_label", "work"), args.get("message_ids"), args.get("hard_delete", False))
                        elif fname == "get_event":
                            res = await self.tools_impl.get_event(args.get("account_label", "work"), args.get("event_id"))
                        elif fname == "update_event":
                            # Filter args for update_event
                            kwargs = {k: v for k, v in args.items() if k not in ["account_label", "event_id"]}
                            res = await self.tools_impl.update_event(args.get("account_label", "work"), args.get("event_id"), **kwargs)
                        elif fname == "delete_event":
                            res = await self.tools_impl.delete_event(args.get("account_label", "work"), args.get("event_id"))
                        elif fname == "respond_to_invitation":
                            res = await self.tools_impl.respond_to_invitation(args.get("account_label", "work"), args.get("event_id"), args.get("response"))
                        elif fname == "mark_email_as_read":
                            res = await self.tools_impl.mark_email_as_read(args.get("account_label", "work"), args.get("message_id"))
                        elif fname == "mark_email_as_unread":
                            res = await self.tools_impl.mark_email_as_unread(args.get("account_label", "work"), args.get("message_id"))
                        elif fname == "star_email":
                            res = await self.tools_impl.star_email(args.get("account_label", "work"), args.get("message_id"))
                        # Missing tools
                        elif fname == "unstar_email":
                            res = await self.tools_impl.unstar_email(args.get("account_label", "work"), args.get("message_id"))
                        elif fname == "send_email":
                            res = await self.tools_impl.send_email(args.get("account_label", "work"), args.get("to", []), args.get("subject", ""), args.get("body", ""))
                        elif fname == "get_email":
                            res = await self.tools_impl.get_email(args.get("account_label", "work"), args.get("message_id"))
                        elif fname == "get_next_event":
                            res = await self.tools_impl.get_next_event(args.get("account_label", "work"))
                        else:
                            res = f"Error: Unknown tool {fname}"
                    except Exception as e:
                        res = f"Error executing {fname}: {str(e)}"
                    
                    return {
                        "role": "tool",
                        "tool_call_id": cid,
                        "content": res
                    }

                tasks.append(execute_tool(function_name, unmasked_args, call_id))

            results = await asyncio.gather(*tasks)
            
            # Mask results using the same mapping
            masked_results = []
            for r in results:
                if isinstance(r.get("content"), str):
                    masked_content, pii_mapping = self.pii.mask(r["content"], mapping=pii_mapping)
                    r["content"] = masked_content
                masked_results.append(r)
            
            messages.extend(masked_results)

        final_msg = "I reached the maximum number of steps and couldn't finish the task."
        return self.pii.unmask(final_msg, pii_mapping)

    def _unmask_structure(self, value, mapping: Dict[str, str]):
        if isinstance(value, str):
            return self.pii.unmask(value, mapping)
        elif isinstance(value, list):
            return [self._unmask_structure(v, mapping) for v in value]
        elif isinstance(value, dict):
            return {k: self._unmask_structure(v, mapping) for k, v in value.items()}
        else:
            return value

    async def get_connected_accounts(self) -> Dict[str, List[Any]]:
        result = await self.db.execute(select(GoogleAccount).where(GoogleAccount.user_id == self.user_id))
        google_accounts = result.scalars().all()
        # Microsoft placeholder if implemented later
        try:
            from app.models.microsoft_account import MicrosoftAccount
            result_ms = await self.db.execute(select(MicrosoftAccount).where(MicrosoftAccount.user_id == self.user_id))
            ms_accounts = result_ms.scalars().all()
        except Exception:
            ms_accounts = []
        return {"google": google_accounts, "microsoft": ms_accounts}
