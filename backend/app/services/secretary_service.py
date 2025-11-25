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

logger = logging.getLogger(__name__)
settings = get_settings()

class SecretaryService:
    def __init__(self, db: AsyncSession, user_id: int):
        self.db = db
        self.user_id = user_id
        self.provider = ProviderFactory.get_provider("openai")
        self.tools_impl = SecretaryTools(db, user_id)

    async def process_request(self, query: str) -> str:
        # 1. Define Tools
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "list_emails",
                    "description": "List emails based on filters. Use this to find unread emails, emails from specific people, or by subject.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "account_label": {"type": "string", "description": "The account label to use (e.g., 'work', 'personal'). Defaults to 'work'."},
                            "filters": {
                                "type": "object",
                                "properties": {
                                    "is_unread": {"type": "boolean"},
                                    "sender": {"type": "string"},
                                    "subject_keyword": {"type": "string"},
                                    "max_results": {"type": "integer"}
                                }
                            }
                        },
                        "required": ["filters"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_events",
                    "description": "List calendar events for a specific time range.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "account_label": {"type": "string", "description": "The account label to use (e.g., 'work', 'personal'). Defaults to 'work'."},
                            "start_time": {"type": "string", "description": "Start time in ISO format (YYYY-MM-DDTHH:MM:SS)."},
                            "end_time": {"type": "string", "description": "End time in ISO format (YYYY-MM-DDTHH:MM:SS)."}
                        },
                        "required": ["start_time", "end_time"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "find_free_slots",
                    "description": "Find free time slots in the calendar.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "account_label": {"type": "string", "description": "The account label to use (e.g., 'work', 'personal'). Defaults to 'work'."},
                            "start_time": {"type": "string", "description": "Start time in ISO format."},
                            "end_time": {"type": "string", "description": "End time in ISO format."},
                            "duration_minutes": {"type": "integer", "description": "Duration of the slot in minutes."}
                        },
                        "required": ["start_time", "end_time", "duration_minutes"]
                    }
                }
            }
        ]

        # 2. Prepare Messages
        current_time = datetime.utcnow().isoformat()
        system_prompt = f"""You are a helpful mail and calendar secretary agent.
Current time (UTC): {current_time}
You have access to tools to read emails and calendars.
When a user asks a question, use the available tools to get the information.
If the user asks for "today", "tomorrow", etc., calculate the ISO dates based on the Current time.
Always return a helpful natural language response to the user based on the tool outputs.
If you need to check multiple accounts, you can call tools multiple times.
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]

        # 3. Agent Loop
        max_turns = 5
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
                return message_content or "I'm done."

            # Execute Tools
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                call_id = tool_call.id
                
                logger.info(f"Executing tool {function_name} with args {arguments}")
                
                result_content = ""
                try:
                    if function_name == "list_emails":
                        result_content = await self.tools_impl.list_emails(
                            arguments.get("account_label", "work"),
                            arguments.get("filters", {})
                        )
                    elif function_name == "list_events":
                        result_content = await self.tools_impl.list_events(
                            arguments.get("account_label", "work"),
                            arguments.get("start_time"),
                            arguments.get("end_time")
                        )
                    elif function_name == "find_free_slots":
                        result_content = await self.tools_impl.find_free_slots(
                            arguments.get("account_label", "work"),
                            arguments.get("start_time"),
                            arguments.get("end_time"),
                            arguments.get("duration_minutes")
                        )
                    else:
                        result_content = f"Error: Unknown tool {function_name}"
                except Exception as e:
                    result_content = f"Error executing {function_name}: {str(e)}"

                # Append tool result
                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": result_content
                })

        return "I reached the maximum number of steps and couldn't finish the task."

    async def get_connected_accounts(self) -> List[GoogleAccount]:
        result = await self.db.execute(select(GoogleAccount).where(GoogleAccount.user_id == self.user_id))
        return result.scalars().all()
