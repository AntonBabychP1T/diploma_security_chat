from __future__ import annotations

from typing import List, Dict, Any, Optional, AsyncGenerator
import time
import json
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.chat import Attachment
from app.providers import ProviderFactory
from app.core.config import get_settings

from .context_builder import ContextBuilder
from .attachment_processor import AttachmentProcessor
from .pii_middleware import PIIMiddleware
from .transcript_persister import TranscriptPersister

logger = logging.getLogger("chat_pipeline")


class ChatPipeline:
    def __init__(self, db: AsyncSession, user_id: int):
        self.db = db
        self.user_id = user_id
        self.settings = get_settings()

        self.context_builder = ContextBuilder(db, user_id)
        self.attachment_processor = AttachmentProcessor()
        self.pii_middleware = PIIMiddleware()
        self.persister = TranscriptPersister(db)
        self.provider_factory = ProviderFactory()

    async def run(
        self,
        chat_id: int,
        content: str,
        attachments: Optional[List[Attachment]] = None,
        style: str = "default",
        provider_name: str = "openai",
        model: Optional[str] = None
    ):
        self.pii_middleware.reset()

        await self.persister.save_user_message(chat_id, content, attachments)

        system_prompt, history = await self.context_builder.build_context(chat_id, style)

        att_parts = await self.attachment_processor.process_attachments(attachments or [])

        masked_history_msgs = await self.pii_middleware.mask_history(history)
        current_masked_content = await self.pii_middleware.mask_user_message(content, att_parts)

        messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        messages.extend(masked_history_msgs)
        messages.append({"role": "user", "content": current_masked_content})

        start_llm = time.time()
        provider = self.provider_factory.get_provider(provider_name)
        response = await provider.generate(
            messages,
            options={
                "model": model,
                "max_completion_tokens": self.settings.OPENAI_MAX_COMPLETION_TOKENS,
            },
        )
        logger.info(f"Chat {chat_id}: LLM generation took {time.time() - start_llm:.4f}s")

        raw_content = response.content or ""
        final_content = await self.pii_middleware.unmask(raw_content)
        if not final_content.strip():
            final_content = "Вибачте, не вдалося згенерувати відповідь."

        meta_data = response.meta_data or {}
        meta_data["style"] = style
        meta_data["masked_used"] = len(self.pii_middleware.mapping) > 0

        msg = await self.persister.save_assistant_message(chat_id, final_content, meta_data)
        await self.persister.update_chat_title_if_new(chat_id, content, final_content)
        return msg

    async def run_stream(
        self,
        chat_id: int,
        content: str,
        attachments: Optional[List[Attachment]] = None,
        style: str = "default",
        provider_name: str = "openai",
        model: Optional[str] = None,
        fastapi_request: Any = None,
    ) -> AsyncGenerator[str, None]:
        self.pii_middleware.reset()

        await self.persister.save_user_message(chat_id, content, attachments)

        system_prompt, history = await self.context_builder.build_context(chat_id, style)

        att_parts = await self.attachment_processor.process_attachments(attachments or [])

        masked_history_msgs = await self.pii_middleware.mask_history(history)
        current_masked_content = await self.pii_middleware.mask_user_message(content, att_parts)

        messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        messages.extend(masked_history_msgs)
        messages.append({"role": "user", "content": current_masked_content})

        provider = self.provider_factory.get_provider(provider_name)
        stream = await provider.stream_generate(
            messages,
            options={
                "model": model,
                "max_completion_tokens": self.settings.OPENAI_MAX_COMPLETION_TOKENS,
            },
        )

        full_chunks: List[str] = []
        start_time = time.time()

        try:
            async for chunk in stream:
                if fastapi_request and await fastapi_request.is_disconnected():
                    await stream.aclose()
                    return

                delta = getattr(chunk.choices[0].delta, "content", "") or ""
                if not delta:
                    continue

                full_chunks.append(delta)
                unmasked_delta = await self.pii_middleware.unmask(delta)
                yield f"data: {json.dumps({'delta': unmasked_delta}, ensure_ascii=False)}\n\n"
        finally:
            try:
                await stream.aclose()
            except Exception:
                pass

            full_raw = "".join(full_chunks)
            final_content = await self.pii_middleware.unmask(full_raw)
            if not final_content.strip():
                final_content = "Вибачте, не вдалося згенерувати відповідь."

            meta = {
                "provider": provider_name,
                "model": model,
                "latency": time.time() - start_time,
                "style": style,
            }

            await self.persister.save_assistant_message(chat_id, final_content, meta)
            await self.persister.update_chat_title_if_new(chat_id, content, final_content)

            yield f"data: {json.dumps({'done': True})}\n\n"
