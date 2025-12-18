from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, Dict, List, Any, Tuple
import json
import logging
from datetime import datetime

from app.core.config import get_settings
from app.core.model_capabilities import ModelRegistry
from app.providers import ProviderFactory
from app.services.secretary_tools import SecretaryTools
from app.services.pii_service import PIIService
from app.services.tools_definition import SECRETARY_TOOLS_DEFINITION
from app.models.google_account import GoogleAccount

logger = logging.getLogger(__name__)
settings = get_settings()


class SecretaryService:
    """
    Secretary agent that can call tools (gmail/calendar).
    Supports both:
      - chat.completions style tool loop (role=tool)
      - responses API style tool loop (function_call_output items)
    """

    def __init__(self, db: AsyncSession, user_id: int):
        self.db = db
        self.user_id = user_id

        # ProviderFactory in твоєму коді зустрічався у двох стилях:
        #  - ProviderFactory().get_provider("openai")
        #  - ProviderFactory.get_provider("openai")
        # Тому робимо безпечний фолбек.
        try:
            self.provider = ProviderFactory().get_provider("openai")
        except Exception:
            self.provider = ProviderFactory.get_provider("openai")

        self.tools_impl = SecretaryTools(db, user_id)
        self.pii = PIIService()

    async def process_request(self, query: str, history: Optional[List[dict]] = None) -> str:
        pii_mapping: Dict[str, str] = {}

        # 1) Mask history
        masked_history: List[dict] = []
        if history:
            for msg in history[-8:]:
                # history може бути dict-ами, або вже готовими структурами
                role = msg.get("role", None)
                content = msg.get("content", None)
                if isinstance(content, str):
                    masked_content, pii_mapping = self.pii.mask(content, mapping=pii_mapping)
                    masked_history.append({"role": role or "user", "content": masked_content})
                else:
                    # якщо не str — залишаємо як є (або можеш конвертити під себе)
                    masked_history.append(msg)

        # 2) Mask current query
        masked_query, pii_mapping = self.pii.mask(query, mapping=pii_mapping)

        # 3) Tools
        tools = SECRETARY_TOOLS_DEFINITION

        # 4) Build system prompt
        current_time = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        system_prompt = f"""You are a helpful mail and calendar secretary agent.
Current time (UTC): {current_time}

You have access to tools to read emails and calendars, find slots, and create/update/delete events.
Use tools directly without asking for extra confirmation unless the user is ambiguous.

If the user asks for "today", "tomorrow", etc., calculate the ISO dates based on Current time (UTC).
Be concise: respond in 1-3 short sentences summarizing the tool results.

IMPORTANT:
- Keep max_results low (5-10) unless the user specifically asks for more.
- Don't repeat the same tool call multiple times.
- Prefer list_events with specific date ranges.
"""

        # 5) Model selection (якщо в тебе є SECRETARY_MODEL у settings — використовуй його)
        model = getattr(settings, "SECRETARY_MODEL", None) or "gpt-5-mini"
        caps = ModelRegistry.get_capabilities(model)
        max_turns = getattr(settings, "SECRETARY_MAX_TURNS", 5)

        if caps.api_type == "responses":
            return await self._run_responses_loop(
                model=model,
                system_prompt=system_prompt,
                masked_history=masked_history,
                masked_query=masked_query,
                tools=tools,
                pii_mapping=pii_mapping,
                max_turns=max_turns,
            )
        else:
            return await self._run_chat_completions_loop(
                model=model,
                system_prompt=system_prompt,
                masked_history=masked_history,
                masked_query=masked_query,
                tools=tools,
                pii_mapping=pii_mapping,
                max_turns=max_turns,
            )

    # -------------------------
    # Chat Completions loop
    # -------------------------
    async def _run_chat_completions_loop(
        self,
        model: str,
        system_prompt: str,
        masked_history: List[dict],
        masked_query: str,
        tools: List[dict],
        pii_mapping: Dict[str, str],
        max_turns: int,
    ) -> str:
        messages: List[dict] = [{"role": "system", "content": system_prompt}]
        messages.extend(masked_history)
        messages.append({"role": "user", "content": masked_query})

        for _ in range(max_turns):
            resp = await self.provider.generate(
                messages,
                options={
                    "model": model,
                    "tools": tools,
                    "tool_choice": "auto",
                    # попросимо провайдера не повертати несеріалізовні штуки
                    "_tool_calls_as_dict": True,
                },
            )

            message_content = resp.content or ""
            tool_calls = resp.tool_calls or []

            # assistant message
            assistant_msg: Dict[str, Any] = {"role": "assistant"}
            if message_content:
                assistant_msg["content"] = message_content
            if tool_calls:
                # гарантовано dict
                assistant_msg["tool_calls"] = [self._normalize_tool_call(tc) for tc in tool_calls]

            messages.append(assistant_msg)

            # no tools -> final
            if not tool_calls:
                final = self.pii.unmask(message_content, pii_mapping) if message_content else "I'm done."
                return final

            # Execute tools
            tool_results = []
            for tc in tool_calls:
                tc_norm = self._normalize_tool_call(tc)
                call_id = tc_norm.get("id") or tc_norm.get("call_id")
                fn_name = tc_norm.get("name")
                args_raw = tc_norm.get("arguments", "{}")

                try:
                    args = json.loads(args_raw) if isinstance(args_raw, str) else (args_raw or {})
                except Exception:
                    args = {}

                # unmask args
                args = self._unmask_structure(args, pii_mapping)

                logger.info(f"Executing tool {fn_name} with args {args}")
                res_text = await self._execute_tool(fn_name, args)

                # mask tool result (same mapping)
                if isinstance(res_text, str):
                    masked_res, pii_mapping = self.pii.mask(res_text, mapping=pii_mapping)
                else:
                    masked_res = str(res_text)

                tool_results.append(
                    {
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": masked_res,
                    }
                )

            messages.extend(tool_results)

        final_msg = "I reached the maximum number of steps and couldn't finish the task."
        return self.pii.unmask(final_msg, pii_mapping)

    # -------------------------
    # Responses API loop
    # -------------------------
    async def _run_responses_loop(
        self,
        model: str,
        system_prompt: str,
        masked_history: List[dict],
        masked_query: str,
        tools: List[dict],
        pii_mapping: Dict[str, str],
        max_turns: int,
    ) -> str:
        # 1) Зроби baseline messages (тільки валідні ролі)
        base_msgs: List[dict] = [{"role": "system", "content": system_prompt}]

        for m in masked_history:
            role = (m.get("role") or "user")
            if role not in {"user", "assistant", "system", "developer"}:
                role = "user"
            content = m.get("content", "")
            if not isinstance(content, (str, list)):
                content = json.dumps(content, ensure_ascii=False)
            base_msgs.append({"role": role, "content": content})

        base_msgs.append({"role": "user", "content": masked_query})

        previous_response_id: Optional[str] = None
        msgs_for_call = base_msgs  # перший раз — повний контекст

        for _ in range(max_turns):
            resp = await self.provider.generate(
                msgs_for_call,
                options={
                    "model": model,
                    "tools": tools,
                    "tool_choice": "auto",
                    "previous_response_id": previous_response_id,  # <-- ключове
                    "_tool_calls_as_dict": True,
                },
            )

            # зберігаємо response_id для chaining
            previous_response_id = (resp.meta_data or {}).get("response_id") or previous_response_id

            tool_calls = resp.tool_calls or []
            content = resp.content or ""

            if not tool_calls:
                return self.pii.unmask(content, pii_mapping) if content else "I'm done."

            # 2) Виконуємо tools і готуємо ТІЛЬКИ tool messages для наступного виклику
            tool_msgs: List[dict] = []
            for tc in tool_calls:
                tc_norm = self._normalize_tool_call(tc)
                call_id = tc_norm.get("id") or tc_norm.get("call_id")
                fn_name = tc_norm.get("name")
                args_raw = tc_norm.get("arguments", "{}")

                try:
                    args = json.loads(args_raw) if isinstance(args_raw, str) else (args_raw or {})
                except Exception:
                    args = {}

                args = self._unmask_structure(args, pii_mapping)

                logger.info(f"Executing tool {fn_name} with args {args}")
                res_text = await self._execute_tool(fn_name, args)

                if isinstance(res_text, str):
                    masked_res, pii_mapping = self.pii.mask(res_text, mapping=pii_mapping)
                else:
                    masked_res = str(res_text)

                tool_msgs.append(
                    {
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": json.dumps({"result": masked_res}, ensure_ascii=False),
                    }
                )

            # наступний виклик робимо ТІЛЬКИ з tool outputs (контекст тримається через previous_response_id)
            msgs_for_call = tool_msgs

        final_msg = "I reached the maximum number of steps and couldn't finish the task."
        return self.pii.unmask(final_msg, pii_mapping)


    # -------------------------
    # Tool execution
    # -------------------------
    async def _execute_tool(self, fname: Optional[str], args: Dict[str, Any]) -> str:
        if not fname:
            return "Error: tool name is missing."

        account_label = args.get("account_label", "work")

        try:
            if fname == "list_emails":
                return await self.tools_impl.list_emails(account_label, args.get("filters", {}) or {})
            if fname == "list_events":
                return await self.tools_impl.list_events(account_label, args.get("start_time"), args.get("end_time"))
            if fname == "find_free_slots":
                return await self.tools_impl.find_free_slots(
                    account_label, args.get("start_time"), args.get("end_time"), args.get("duration_minutes")
                )
            if fname == "create_event":
                return await self.tools_impl.create_event(
                    account_label,
                    args.get("summary", "Untitled"),
                    args.get("start_time"),
                    args.get("end_time"),
                    args.get("attendees", []) or [],
                )
            if fname == "reply_email":
                return await self.tools_impl.reply_email(
                    account_label, args.get("message_id"), args.get("body"), args.get("reply_all", False)
                )
            if fname == "forward_email":
                return await self.tools_impl.forward_email(
                    account_label, args.get("message_id"), args.get("to", []), args.get("body", "")
                )
            if fname == "delete_emails":
                return await self.tools_impl.delete_emails(
                    account_label, args.get("message_ids", []), args.get("hard_delete", False)
                )
            if fname == "get_event":
                return await self.tools_impl.get_event(account_label, args.get("event_id"))
            if fname == "update_event":
                kwargs = {k: v for k, v in args.items() if k not in ["account_label", "event_id"]}
                return await self.tools_impl.update_event(account_label, args.get("event_id"), **kwargs)
            if fname == "delete_event":
                return await self.tools_impl.delete_event(account_label, args.get("event_id"))
            if fname == "respond_to_invitation":
                return await self.tools_impl.respond_to_invitation(account_label, args.get("event_id"), args.get("response"))
            if fname == "mark_email_as_read":
                return await self.tools_impl.mark_email_as_read(account_label, args.get("message_id"))
            if fname == "mark_email_as_unread":
                return await self.tools_impl.mark_email_as_unread(account_label, args.get("message_id"))
            if fname == "star_email":
                return await self.tools_impl.star_email(account_label, args.get("message_id"))
            if fname == "unstar_email":
                return await self.tools_impl.unstar_email(account_label, args.get("message_id"))
            if fname == "send_email":
                return await self.tools_impl.send_email(
                    account_label, args.get("to", []), args.get("subject", ""), args.get("body", "")
                )
            if fname == "get_email":
                return await self.tools_impl.get_email(account_label, args.get("message_id"))
            if fname == "get_next_event":
                return await self.tools_impl.get_next_event(account_label)

            return f"Error: Unknown tool {fname}"
        except Exception as e:
            logger.exception(f"Error executing tool {fname}: {e}")
            return f"Error executing {fname}: {str(e)}"

    # -------------------------
    # Helpers
    # -------------------------
    def _normalize_tool_call(self, tool_call: Any) -> Dict[str, Any]:
        """
        Make tool call always dict:
          - chat.completions tool call object
          - dict already
          - responses function_call item dict
        Output schema:
          {
            "id": "...",          # chat.completions compatible
            "call_id": "...",     # responses compatible
            "name": "...",
            "arguments": "json-string"
          }
        """
        if tool_call is None:
            return {}

        # already dict
        if isinstance(tool_call, dict):
            # Possible shapes:
            # 1) {"id":..., "function": {"name":..., "arguments":...}}
            # 2) {"call_id":..., "name":..., "arguments":...}
            if "function" in tool_call and isinstance(tool_call["function"], dict):
                return {
                    "id": tool_call.get("id"),
                    "call_id": tool_call.get("id") or tool_call.get("call_id"),
                    "name": tool_call["function"].get("name"),
                    "arguments": tool_call["function"].get("arguments", "{}"),
                }
            return {
                "id": tool_call.get("id") or tool_call.get("call_id"),
                "call_id": tool_call.get("call_id") or tool_call.get("id"),
                "name": tool_call.get("name"),
                "arguments": tool_call.get("arguments", "{}"),
            }

        # pydantic / openai tool call object (chat.completions)
        fn = getattr(tool_call, "function", None)
        if fn is not None:
            return {
                "id": getattr(tool_call, "id", None),
                "call_id": getattr(tool_call, "id", None),
                "name": getattr(fn, "name", None),
                "arguments": getattr(fn, "arguments", "{}"),
            }

        # fallback
        return {"id": None, "call_id": None, "name": None, "arguments": "{}"}

    def _unmask_structure(self, value: Any, mapping: Dict[str, str]) -> Any:
        if isinstance(value, str):
            return self.pii.unmask(value, mapping)
        if isinstance(value, list):
            return [self._unmask_structure(v, mapping) for v in value]
        if isinstance(value, dict):
            return {k: self._unmask_structure(v, mapping) for k, v in value.items()}
        return value

    async def get_connected_accounts(self) -> Dict[str, List[Any]]:
        # залишив твою логіку
        result = await self.db.execute(select(GoogleAccount).where(GoogleAccount.user_id == self.user_id))
        google_accounts = result.scalars().all()

        try:
            from app.models.microsoft_account import MicrosoftAccount
            result_ms = await self.db.execute(select(MicrosoftAccount).where(MicrosoftAccount.user_id == self.user_id))
            ms_accounts = result_ms.scalars().all()
        except Exception:
            ms_accounts = []

        return {"google": google_accounts, "microsoft": ms_accounts}
