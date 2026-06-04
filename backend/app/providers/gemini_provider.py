from __future__ import annotations

import base64
import binascii
import logging
from types import SimpleNamespace
from typing import List, Dict, Any, Optional, Tuple

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:
    genai = None
    genai_types = None

from app.core.config import get_settings
from .base import LLMProvider, ProviderResponse

settings = get_settings()
logger = logging.getLogger(__name__)

class GeminiProvider(LLMProvider):
    def __init__(self):
        if not genai:
            raise ImportError("google-genai package is required for GeminiProvider")
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not configured")
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.default_model = "gemini-2.5-flash"

    def _resolve_model_id(self, model_name: Optional[str]) -> str:
        model_id = model_name or self.default_model
        alias_map = {
            "gemini-2.5-flash": "gemini-2.5-flash",
            "gemini-2.5-flash-lite": "gemini-2.5-flash-lite",
        }
        model_id = alias_map.get(model_id, model_id)
        if model_id.startswith("models/"):
            model_id = model_id.removeprefix("models/")
        return model_id

    def _get_option(self, options: Any, key: str, default: Any = None) -> Any:
        if options is None:
            return default
        if isinstance(options, dict):
            return options.get(key, default)
        return getattr(options, key, default)

    def _content_to_text(self, content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
            return "\n".join(part for part in text_parts if part)
        return "" if content is None else str(content)

    def _image_part_from_url(self, item: Dict[str, Any]):
        url = (item.get("image_url") or {}).get("url", "")
        mime_type = item.get("mime_type", "image/jpeg")

        if url.startswith("data:"):
            header, _, encoded_data = url.partition(",")
            mime_part = header.removeprefix("data:").removesuffix(";base64")
            if mime_part:
                mime_type = mime_part
            try:
                return genai_types.Part.from_bytes(
                    data=base64.b64decode(encoded_data, validate=True),
                    mime_type=mime_type,
                )
            except (binascii.Error, ValueError) as exc:
                logger.warning("Invalid base64 image attachment for Gemini: %s", exc)
                return None

        if url.startswith(("http://", "https://", "gs://")):
            return genai_types.Part.from_uri(file_uri=url, mime_type=mime_type)

        try:
            return genai_types.Part.from_bytes(
                data=base64.b64decode(url, validate=True),
                mime_type=mime_type,
            )
        except (binascii.Error, ValueError) as exc:
            logger.warning("Unsupported image attachment for Gemini: %s", exc)
            return None

    def _convert_content_parts(self, content: Any) -> List[Any]:
        if isinstance(content, str):
            return [genai_types.Part.from_text(text=content)]

        if not isinstance(content, list):
            return [genai_types.Part.from_text(text=self._content_to_text(content))]

        parts: List[Any] = []
        for item in content:
            if isinstance(item, str):
                parts.append(genai_types.Part.from_text(text=item))
                continue

            if not isinstance(item, dict):
                continue

            if item.get("type") == "text":
                parts.append(genai_types.Part.from_text(text=item.get("text", "")))
            elif item.get("type") == "image_url":
                image_part = self._image_part_from_url(item)
                if image_part:
                    parts.append(image_part)

        return parts

    def _convert_messages(self, messages: List[Dict[str, Any]]) -> Tuple[Optional[str], List[Any]]:
        system_instructions: List[str] = []
        contents: List[Any] = []

        for message in messages:
            role = message.get("role")
            content = message.get("content", "")

            if role == "system":
                system_text = self._content_to_text(content)
                if system_text:
                    system_instructions.append(system_text)
                continue

            gemini_role = "model" if role in {"assistant", "model"} else "user"
            parts = self._convert_content_parts(content)
            if parts:
                contents.append(genai_types.Content(role=gemini_role, parts=parts))

        if not contents:
            contents.append(genai_types.Content(
                role="user",
                parts=[genai_types.Part.from_text(text="")]
            ))

        system_instruction = "\n\n".join(system_instructions) or None
        return system_instruction, contents

    def _build_config(self, options: Any, system_instruction: Optional[str]):
        config: Dict[str, Any] = {}

        temperature = self._get_option(options, "temperature")
        if temperature is not None:
            config["temperature"] = temperature

        max_output_tokens = (
            self._get_option(options, "max_output_tokens")
            or self._get_option(options, "max_completion_tokens")
        )
        if max_output_tokens:
            config["max_output_tokens"] = max_output_tokens

        if system_instruction:
            config["system_instruction"] = system_instruction

        return genai_types.GenerateContentConfig(**config) if config else None

    def _extract_usage(self, response: Any) -> Dict[str, Any]:
        usage = getattr(response, "usage_metadata", None)
        if not usage:
            return {}
        if hasattr(usage, "model_dump"):
            return usage.model_dump(exclude_none=True)
        return {
            "prompt_token_count": getattr(usage, "prompt_token_count", None),
            "candidates_token_count": getattr(usage, "candidates_token_count", None),
            "total_token_count": getattr(usage, "total_token_count", None),
        }

    def _stream_chunk(self, content: str):
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    delta=SimpleNamespace(content=content)
                )
            ]
        )

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        options: Optional[Dict[str, Any]] = None
    ) -> ProviderResponse:
        options = options or {}
        model_name = self._get_option(options, "model", self.default_model)
        model_id = self._resolve_model_id(model_name)
        system_instruction, contents = self._convert_messages(messages)
        config = self._build_config(options, system_instruction)

        try:
            response = await self.client.aio.models.generate_content(
                model=model_id,
                contents=contents,
                config=config,
            )
            text = response.text or ""

            return ProviderResponse(
                content=text,
                meta_data={
                    "provider": "gemini",
                    "model": model_name,
                    "usage": self._extract_usage(response),
                }
            )
        except Exception as e:
            logger.exception("Gemini Provider Error: %s", e)
            raise e

    async def stream_generate(
        self,
        messages: List[Dict[str, Any]],
        options: Optional[Dict[str, Any]] = None
    ):
        options = options or {}
        model_name = self._get_option(options, "model", self.default_model)
        model_id = self._resolve_model_id(model_name)
        system_instruction, contents = self._convert_messages(messages)
        config = self._build_config(options, system_instruction)

        async def generator():
            response_stream = await self.client.aio.models.generate_content_stream(
                model=model_id,
                contents=contents,
                config=config,
            )

            try:
                async for chunk in response_stream:
                    text = chunk.text or ""
                    if text:
                        yield self._stream_chunk(text)
            finally:
                close = getattr(response_stream, "aclose", None)
                if close:
                    await close()

        return generator()
