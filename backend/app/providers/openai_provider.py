from __future__ import annotations

from typing import Dict, Any, Optional, List, Union, Callable, Awaitable
import json
import time
import logging
import openai

from app.core.config import get_settings
from app.core.model_capabilities import ModelRegistry
from .base import LLMProvider, ProviderResponse

settings = get_settings()
logger = logging.getLogger(__name__)


JSONToolCall = Dict[str, Any]
ToolRunner = Callable[[str, Dict[str, Any]], Awaitable[Union[str, Dict[str, Any], List[Any]]]]


class OpenAIProvider(LLMProvider):
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.default_model = "gpt-5-mini"

    # ----------------------------
    # Helpers: JSON-safe conversion
    # ----------------------------

    def _sanitize_tool_calls(self, tool_calls: Any) -> List[JSONToolCall]:
        """
        Always return tool_calls as plain JSON-serializable dicts:
          {"id": "...", "type":"function", "function": {"name":"...", "arguments":"..."}}
        """
        if not tool_calls:
            return []

        out: List[JSONToolCall] = []
        for tc in tool_calls:
            if tc is None:
                continue
            if isinstance(tc, dict):
                out.append(tc)
                continue
            # Pydantic v2 objects (OpenAI SDK types often support model_dump)
            if hasattr(tc, "model_dump"):
                out.append(tc.model_dump())
                continue
            # Pydantic v1
            if hasattr(tc, "dict"):
                out.append(tc.dict())
                continue

            # Fallback: try attribute-based extraction
            try:
                fn = getattr(tc, "function", None)
                fn_name = getattr(fn, "name", None) if fn else None
                fn_args = getattr(fn, "arguments", None) if fn else None
                out.append({
                    "id": getattr(tc, "id", None),
                    "type": getattr(tc, "type", "function"),
                    "function": {"name": fn_name, "arguments": fn_args},
                })
            except Exception:
                # don't crash on unknown shapes
                continue

        # remove empties
        cleaned: List[JSONToolCall] = []
        for item in out:
            if not isinstance(item, dict):
                continue
            if "function" in item and isinstance(item["function"], dict):
                cleaned.append(item)
        return cleaned

    def _convert_multimodal_content_for_chat(self, content: Any) -> Any:
        """
        Clean content parts for Chat Completions payload:
          - keep only {"type":"text","text":...} and {"type":"image_url","image_url":{"url":...}}
        """
        if not isinstance(content, list):
            return content

        new_content = []
        for item in content:
            if not isinstance(item, dict):
                continue
            t = item.get("type")
            if t == "image_url":
                img = item.get("image_url") or {}
                url = img.get("url")
                if not url:
                    continue
                new_content.append({"type": "image_url", "image_url": {"url": url}})
            elif t == "text":
                new_content.append({"type": "text", "text": item.get("text", "")})
        return new_content

    def _sanitize_messages_for_chat_completions(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Make messages JSON-serializable and compliant.
        """
        cleaned: List[Dict[str, Any]] = []

        for m in messages:
            if not isinstance(m, dict):
                continue

            role = m.get("role")
            msg: Dict[str, Any] = {"role": role}

            # content
            content = m.get("content")
            msg["content"] = self._convert_multimodal_content_for_chat(content)

            # tool messages support
            if role == "tool":
                # Chat Completions expects tool_call_id
                if "tool_call_id" in m:
                    msg["tool_call_id"] = m["tool_call_id"]
                # optional tool name
                if "name" in m:
                    msg["name"] = m["name"]

            # assistant tool calls (if caller manually appends them)
            if "tool_calls" in m:
                msg["tool_calls"] = self._sanitize_tool_calls(m["tool_calls"])

            cleaned.append(msg)

        return cleaned

    def _convert_tools_for_responses(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Chat-completions function tool format часто:
          {"type":"function","function":{"name":...,"description":...,"parameters":...}}
        Responses API очікує:
          {"type":"function","name":...,"description":...,"parameters":...}
        """
        converted = []
        for t in tools:
            if t.get("type") == "function" and isinstance(t.get("function"), dict):
                fn = t["function"]
                new_tool = {
                    "type": "function",
                    "name": fn.get("name"),
                    "description": fn.get("description"),
                    "parameters": fn.get("parameters"),
                }
                converted.append({k: v for k, v in new_tool.items() if v is not None})
            else:
                converted.append(t)
        return converted

    def _tool_call_obj_to_dict(self, tc: Any) -> Dict[str, Any]:
            """
            Convert chat.completions tool_call object -> dict
            """
            if tc is None:
                return {}
            if isinstance(tc, dict):
                # already dict
                if "function" in tc and isinstance(tc["function"], dict):
                    return {
                        "id": tc.get("id"),
                        "call_id": tc.get("id") or tc.get("call_id"),
                        "name": tc["function"].get("name"),
                        "arguments": tc["function"].get("arguments", "{}"),
                    }
                return {
                    "id": tc.get("id") or tc.get("call_id"),
                    "call_id": tc.get("call_id") or tc.get("id"),
                    "name": tc.get("name"),
                    "arguments": tc.get("arguments", "{}"),
                }

            fn = getattr(tc, "function", None)
            if fn is not None:
                return {
                    "id": getattr(tc, "id", None),
                    "call_id": getattr(tc, "id", None),
                    "name": getattr(fn, "name", None),
                    "arguments": getattr(fn, "arguments", "{}"),
                }
            return {}

    def _build_responses_input_and_instructions(
        self, messages: List[Dict[str, Any]]
    ) -> tuple[Optional[str], List[Dict[str, Any]]]:
        """
        For Responses API:
          - pull first system message into `instructions`
          - convert role="tool" messages into function_call_output items
          - keep other messages as-is (role/content), but ensure JSON-safe content
        """
        instructions: Optional[str] = None
        input_items: List[Dict[str, Any]] = []

        for idx, m in enumerate(messages):
            if not isinstance(m, dict):
                continue
            role = m.get("role")

            if role == "system" and instructions is None:
                # store as instructions
                c = m.get("content", "")
                instructions = c if isinstance(c, str) else json.dumps(c, ensure_ascii=False)
                continue

            if role == "tool":
                # Convert to function_call_output item
                call_id = m.get("tool_call_id") or m.get("call_id")
                output = m.get("content", "")
                if call_id:
                    input_items.append({
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": output if isinstance(output, str) else json.dumps(output, ensure_ascii=False),
                    })
                continue

            # Normal message item
            content = m.get("content", "")
            if isinstance(content, list):
                # Convert our internal "text"/"image_url" parts to Responses-friendly input parts (best-effort).
                # Якщо твій перший запит уже працював — це не зламає, бо залишаємо структуру близьку.
                parts: List[Dict[str, Any]] = []
                for item in content:
                    if not isinstance(item, dict):
                        continue
                    t = item.get("type")
                    if t == "text":
                        parts.append({"type": "input_text", "text": item.get("text", "")})
                    elif t == "image_url":
                        img = item.get("image_url") or {}
                        url = img.get("url")
                        if url:
                            parts.append({"type": "input_image", "image_url": url})
                input_items.append({"role": role, "content": parts})
            else:
                input_items.append({"role": role, "content": content})

        return instructions, input_items

    def _extract_responses_tool_calls(self, response: Any) -> List[JSONToolCall]:
        """
        Extract function calls from response.output (Responses API).
        Return JSON dicts compatible with chat tool_calls shape.
        """
        tool_calls: List[JSONToolCall] = []
        output = getattr(response, "output", None)
        if not output:
            return tool_calls

        for item in output:
            # SDK can give dict-like or typed objects
            itype = None
            if isinstance(item, dict):
                itype = item.get("type")
                if itype == "function_call":
                    tool_calls.append({
                        "id": item.get("call_id"),
                        "type": "function",
                        "function": {
                            "name": item.get("name"),
                            "arguments": item.get("arguments"),
                        },
                    })
            else:
                itype = getattr(item, "type", None)
                if itype == "function_call":
                    tool_calls.append({
                        "id": getattr(item, "call_id", None),
                        "type": "function",
                        "function": {
                            "name": getattr(item, "name", None),
                            "arguments": getattr(item, "arguments", None),
                        },
                    })

        return tool_calls

    # ----------------------------
    # Public API
    # ----------------------------

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        options: Optional[Dict[str, Any]] = None
    ) -> ProviderResponse:
        options = options or {}

        model = options.get("model") or self.default_model
        caps = ModelRegistry.get_capabilities(model)

        configured_max = options.get("max_completion_tokens") or settings.OPENAI_MAX_COMPLETION_TOKENS
        if caps.max_output_tokens:
            configured_max = min(configured_max, caps.max_output_tokens)

        temperature = options.get("temperature", None)
        if temperature is not None and not caps.supports_temperature:
            temperature = None

        tools = options.get("tools")
        tool_choice = options.get("tool_choice")
        previous_response_id = options.get("previous_response_id")

        # optional tool runner (to auto-loop)
        tool_runner: Optional[ToolRunner] = options.get("tool_runner")

        try:
            if caps.api_type == "responses":
                # Responses API
                instructions, input_items = self._build_responses_input_and_instructions(messages)

                req: Dict[str, Any] = {
                    "model": model,
                    "input": input_items,
                    "max_output_tokens": configured_max,
                }
                if instructions:
                    req["instructions"] = instructions
                if temperature is not None:
                    req["temperature"] = temperature
                if tools:
                    req["tools"] = self._convert_tools_for_responses(tools)
                if tool_choice:
                    req["tool_choice"] = tool_choice
                if previous_response_id:
                    req["previous_response_id"] = previous_response_id

                start = time.time()
                response = await self.client.responses.create(**req)
                latency = time.time() - start

                content = getattr(response, "output_text", "") or ""
                tool_calls = self._extract_responses_tool_calls(response)

                # If auto-loop enabled, run tools and call again until no tool calls
                if tool_runner and tool_calls:
                    # execute all tool calls
                    tool_msgs: List[Dict[str, Any]] = []
                    for tc in tool_calls:
                        fn = tc.get("function", {}) or {}
                        name = fn.get("name")
                        arg_str = fn.get("arguments") or "{}"
                        try:
                            args = json.loads(arg_str) if isinstance(arg_str, str) else (arg_str or {})
                        except Exception:
                            args = {}

                        out = await tool_runner(name, args)
                        # store as role=tool message with tool_call_id
                        tool_msgs.append({
                            "role": "tool",
                            "tool_call_id": tc.get("id"),
                            "content": out if isinstance(out, str) else json.dumps(out, ensure_ascii=False),
                            "name": name,
                        })

                    # second call chained with previous_response_id
                    messages2 = messages + tool_msgs
                    return await self.generate(
                        messages2,
                        options={
                            **options,
                            "previous_response_id": getattr(response, "id", None),
                            # prevent infinite recursion
                            "tool_runner": tool_runner,
                        },
                    )

                meta_data: Dict[str, Any] = {
                    "provider": "openai",
                    "model": model,
                    "finish_reason": getattr(response, "status", None) or "stop",
                    "response_id": getattr(response, "id", None),
                    "latency": latency,
                }
                usage = getattr(response, "usage", None)
                if usage and hasattr(usage, "model_dump"):
                    meta_data["usage"] = usage.model_dump()
                elif usage and isinstance(usage, dict):
                    meta_data["usage"] = usage

                if tool_calls:
                    meta_data["tool_calls"] = tool_calls  # already JSON-safe

                logger.info(f"OpenAI Response (responses): model={model}, content_len={len(content)}, tool_calls={len(tool_calls)}")
                if not content and tool_calls:
                    logger.warning("Empty content is expected when model requests tools (responses API).")

                return ProviderResponse(content=content, tool_calls=tool_calls, meta_data=meta_data)

            # ----------------------------
            # Chat Completions API
            # ----------------------------
            cleaned_messages = self._sanitize_messages_for_chat_completions(messages)

            req: Dict[str, Any] = {
                "model": model,
                "messages": cleaned_messages,
                "max_completion_tokens": configured_max,
            }
            if temperature is not None:
                req["temperature"] = temperature
            if tools:
                req["tools"] = tools
            if tool_choice:
                req["tool_choice"] = tool_choice

            start = time.time()
            response = await self.client.chat.completions.create(**req)
            latency = time.time() - start

            msg = response.choices[0].message
            content = msg.content or ""
            tool_calls_raw = getattr(msg, "tool_calls", None)
            tool_calls = self._sanitize_tool_calls(tool_calls_raw)

            meta_data: Dict[str, Any] = {
                "provider": "openai",
                "model": model,
                "finish_reason": response.choices[0].finish_reason,
                "latency": latency,
            }
            if response.usage:
                meta_data["usage"] = response.usage.model_dump()

            if tool_calls:
                meta_data["tool_calls"] = tool_calls

            logger.info(f"OpenAI Response (chat): model={model}, content_len={len(content)}, tool_calls={len(tool_calls)}")

            # Optional auto-loop for chat tool calling
            if tool_runner and tool_calls:
                # append assistant tool-call message + tool outputs and call again
                assistant_tool_msg = {
                    "role": "assistant",
                    "content": "",          # typically empty when tool calls
                    "tool_calls": tool_calls,
                }
                tool_msgs: List[Dict[str, Any]] = []
                for tc in tool_calls:
                    fn = tc.get("function", {}) or {}
                    name = fn.get("name")
                    arg_str = fn.get("arguments") or "{}"
                    try:
                        args = json.loads(arg_str) if isinstance(arg_str, str) else (arg_str or {})
                    except Exception:
                        args = {}

                    out = await tool_runner(name, args)
                    tool_msgs.append({
                        "role": "tool",
                        "tool_call_id": tc.get("id"),
                        "content": out if isinstance(out, str) else json.dumps(out, ensure_ascii=False),
                        "name": name,
                    })

                messages2 = messages + [assistant_tool_msg] + tool_msgs
                return await self.generate(messages2, options={**options, "tool_runner": tool_runner})

            return ProviderResponse(content=content, tool_calls=tool_calls, meta_data=meta_data)

        except Exception as e:
            logger.exception(f"OpenAI Provider Error: {e}")
            raise

    async def _normalize_responses_stream(self, stream):
        """
        Convert Responses streaming events to a ChatCompletions-like shape:
          chunk.choices[0].delta.content
        """
        from types import SimpleNamespace

        async for evt in stream:
            event_type = getattr(evt, "type", "") or ""
            if event_type == "response.output_text.delta":
                delta = getattr(evt, "delta", "") or ""
                if delta:
                    yield SimpleNamespace(
                        choices=[
                            SimpleNamespace(
                                delta=SimpleNamespace(content=delta),
                                finish_reason=None,
                            )
                        ]
                    )

    async def stream_generate(
        self,
        messages: List[Dict[str, Any]],
        options: Optional[Dict[str, Any]] = None
    ):
        options = options or {}

        model = options.get("model") or self.default_model
        caps = ModelRegistry.get_capabilities(model)

        configured_max = options.get("max_completion_tokens") or settings.OPENAI_MAX_COMPLETION_TOKENS
        if caps.max_output_tokens:
            configured_max = min(configured_max, caps.max_output_tokens)

        temperature = options.get("temperature", None)
        if temperature is not None and not caps.supports_temperature:
            temperature = None

        tools = options.get("tools")
        tool_choice = options.get("tool_choice")
        previous_response_id = options.get("previous_response_id")

        try:
            if caps.api_type == "responses":
                instructions, input_items = self._build_responses_input_and_instructions(messages)

                req: Dict[str, Any] = {
                    "model": model,
                    "input": input_items,
                    "max_output_tokens": configured_max,
                    "stream": True,
                }
                if instructions:
                    req["instructions"] = instructions
                if temperature is not None:
                    req["temperature"] = temperature
                if tools:
                    req["tools"] = self._convert_tools_for_responses(tools)
                if tool_choice:
                    req["tool_choice"] = tool_choice
                if previous_response_id:
                    req["previous_response_id"] = previous_response_id

                raw_stream = await self.client.responses.create(**req)
                return self._normalize_responses_stream(raw_stream)

            # chat completions streaming
            cleaned_messages = self._sanitize_messages_for_chat_completions(messages)

            req: Dict[str, Any] = {
                "model": model,
                "messages": cleaned_messages,
                "max_completion_tokens": configured_max,
                "stream": True,
            }
            if temperature is not None:
                req["temperature"] = temperature
            if tools:
                req["tools"] = tools
            if tool_choice:
                req["tool_choice"] = tool_choice

            return await self.client.chat.completions.create(**req)

        except Exception as e:
            logger.exception(f"OpenAI Stream Error: {e}")
            raise
