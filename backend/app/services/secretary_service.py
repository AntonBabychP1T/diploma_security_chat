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

    async def process_request(self, query: str, history: Optional[List[dict]] = None) -> str:
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
            ,
            {
                "type": "function",
                "function": {
                    "name": "create_event",
                    "description": "Create a calendar event with optional attendees.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "account_label": {"type": "string", "description": "The account label to use (e.g., 'work', 'personal'). Defaults to 'work'."},
                            "summary": {"type": "string"},
                            "start_time": {"type": "string", "description": "Start time ISO (YYYY-MM-DDTHH:MM:SS)"},
                            "end_time": {"type": "string", "description": "End time ISO (YYYY-MM-DDTHH:MM:SS)"},
                            "attendees": {"type": "array", "items": {"type": "string"}, "description": "List of attendee emails"}
                        },
                        "required": ["summary", "start_time", "end_time"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "reply_email",
                    "description": "Reply to an email.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "account_label": {"type": "string", "description": "Account label (default 'work')"},
                            "message_id": {"type": "string"},
                            "body": {"type": "string"},
                            "reply_all": {"type": "boolean"}
                        },
                        "required": ["message_id", "body"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "forward_email",
                    "description": "Forward an email.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "account_label": {"type": "string", "description": "Account label (default 'work')"},
                            "message_id": {"type": "string"},
                            "to": {"type": "array", "items": {"type": "string"}},
                            "body": {"type": "string"}
                        },
                        "required": ["message_id", "to", "body"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_emails",
                    "description": "Delete emails by ID.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "account_label": {"type": "string", "description": "Account label (default 'work')"},
                            "message_ids": {"type": "array", "items": {"type": "string"}},
                            "hard_delete": {"type": "boolean"}
                        },
                        "required": ["message_ids"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_event",
                    "description": "Get details of a specific calendar event.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "account_label": {"type": "string", "description": "Account label (default 'work')"},
                            "event_id": {"type": "string"}
                        },
                        "required": ["event_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_event",
                    "description": "Update an existing calendar event.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "account_label": {"type": "string", "description": "Account label (default 'work')"},
                            "event_id": {"type": "string"},
                            "summary": {"type": "string"},
                            "description": {"type": "string"},
                            "location": {"type": "string"},
                            "start_time": {"type": "string", "description": "ISO format"},
                            "end_time": {"type": "string", "description": "ISO format"},
                            "attendees": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["event_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_event",
                    "description": "Delete a calendar event.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "account_label": {"type": "string", "description": "Account label (default 'work')"},
                            "event_id": {"type": "string"}
                        },
                        "required": ["event_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "respond_to_invitation",
                    "description": "Respond to a calendar invitation.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "account_label": {"type": "string", "description": "Account label (default 'work')"},
                            "event_id": {"type": "string"},
                            "response": {"type": "string", "enum": ["accepted", "declined", "tentative"]}
                        },
                        "required": ["event_id", "response"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "mark_email_as_read",
                    "description": "Mark an email as read.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "account_label": {"type": "string", "description": "Account label (default 'work')"},
                            "message_id": {"type": "string"}
                        },
                        "required": ["message_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "mark_email_as_unread",
                    "description": "Mark an email as unread.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "account_label": {"type": "string", "description": "Account label (default 'work')"},
                            "message_id": {"type": "string"}
                        },
                        "required": ["message_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "star_email",
                    "description": "Star/flag an email as important.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "account_label": {"type": "string", "description": "Account label (default 'work')"},
                            "message_id": {"type": "string"}
                        },
                        "required": ["message_id"]
                    }
                }
            }
        ]

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
        if history:
            messages.extend(history[-8:])  # keep limited context
        messages.append({"role": "user", "content": query})

        # 3. Agent Loop
        max_turns = 5
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
                return message_content or "I'm done."

            # Execute Tools in Parallel
            tasks = []
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                call_id = tool_call.id
                
                logger.info(f"Executing tool {function_name} with args {arguments}")
                
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
                        else:
                            res = f"Error: Unknown tool {fname}"
                    except Exception as e:
                        res = f"Error executing {fname}: {str(e)}"
                    
                    return {
                        "role": "tool",
                        "tool_call_id": cid,
                        "content": res
                    }

                tasks.append(execute_tool(function_name, arguments, call_id))

            results = await asyncio.gather(*tasks)
            messages.extend(results)

        return "I reached the maximum number of steps and couldn't finish the task."

    async def get_connected_accounts(self) -> List[GoogleAccount]:
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
