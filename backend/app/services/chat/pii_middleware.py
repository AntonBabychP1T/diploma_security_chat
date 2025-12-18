from __future__ import annotations

from typing import Tuple, Dict, List, Any, Optional, Union
from app.services.pii_service import PIIService
import asyncio


class PIIMiddleware:
    def __init__(self):
        self.pii_service = PIIService()
        self.mapping: Dict[str, str] = {}

    def reset(self) -> None:
        # важливо: не тримати mapping між різними pipeline.run()
        self.mapping = {}

    async def mask_history(self, messages: List[Any]) -> List[Dict[str, Any]]:
        masked_messages = []
        for msg in messages:
            masked_content, self.mapping = await asyncio.to_thread(self.pii_service.mask, msg.content, self.mapping)
            masked_messages.append({"role": msg.role, "content": masked_content})
        return masked_messages

    async def mask_user_message(
        self,
        content: str,
        attachments_parts: Optional[List[Dict[str, Any]]] = None
    ) -> Union[str, List[Dict[str, Any]]]:
        masked_content, self.mapping = await asyncio.to_thread(self.pii_service.mask, content, self.mapping)

        if attachments_parts:
            parts = [{"type": "text", "text": masked_content}]
            parts.extend(attachments_parts)
            return parts

        return masked_content

    async def unmask(self, text: str) -> str:
        if not text:
            return ""
        return await asyncio.to_thread(self.pii_service.unmask, text, self.mapping)
