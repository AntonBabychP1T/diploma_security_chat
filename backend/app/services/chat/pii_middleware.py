from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Union

from app.services.pii_service import PIIService


class PIIMiddleware:
    def __init__(self):
        self.pii_service = PIIService()
        self.session = self.pii_service.create_session()
        self.stream_buffering = self.pii_service.stream_buffering

    def reset(self) -> None:
        # Важливо: не тримати session між різними pipeline.run()
        self.session = self.pii_service.create_session()

    async def mask_history(self, messages: List[Any]) -> List[Dict[str, Any]]:
        masked_messages: List[Dict[str, Any]] = []
        for msg in messages:
            content = getattr(msg, "content", None)
            if isinstance(content, str):
                masked_content = await asyncio.to_thread(self.session.mask_text, content)
            else:
                masked_content = content
            masked_messages.append({"role": msg.role, "content": masked_content})
        return masked_messages

    async def mask_user_message(
        self,
        content: str,
        attachments_parts: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[str, List[Dict[str, Any]]]:
        masked_content = await asyncio.to_thread(self.session.mask_text, content)

        if attachments_parts:
            parts: List[Dict[str, Any]] = [{"type": "text", "text": masked_content}]
            for part in attachments_parts:
                if not isinstance(part, dict):
                    parts.append(part)
                    continue

                if part.get("type") == "text" and isinstance(part.get("text"), str):
                    masked_text = await asyncio.to_thread(self.session.mask_text, part["text"])
                    new_part = dict(part)
                    new_part["text"] = masked_text
                    parts.append(new_part)
                else:
                    parts.append(part)
            return parts

        return masked_content

    async def unmask(self, text: str) -> str:
        if not text:
            return ""
        return await asyncio.to_thread(self.session.unmask_text, text)

    async def unmask_chunk(self, text: str) -> str:
        if not text:
            return ""
        if not self.stream_buffering:
            return await self.unmask(text)
        return await asyncio.to_thread(self.session.unmask_chunk, text)

    async def flush_unmask_tail(self) -> str:
        if not self.stream_buffering:
            return ""
        return await asyncio.to_thread(self.session.flush_unmask_tail)

    @property
    def mapping(self) -> Dict[str, str]:
        return self.session.token_to_value
