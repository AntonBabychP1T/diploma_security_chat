from __future__ import annotations

from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.chat import Message, Chat
from app.schemas.chat import Attachment
from app.utils.logger import get_logger
from sqlalchemy import select

logger = get_logger("transcript_persister")


class TranscriptPersister:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_user_message(self, chat_id: int, content: str, attachments: Optional[list[Attachment]] = None) -> Message:
        meta_data: Dict[str, Any] = {}
        if attachments:
            meta_data["attachments"] = [{"name": a.name, "type": a.type} for a in attachments]

        user_message = Message(chat_id=chat_id, role="user", content=content, meta_data=meta_data)
        self.db.add(user_message)
        await self.db.commit()
        await self.db.refresh(user_message)
        return user_message

    async def save_assistant_message(self, chat_id: int, content: str, meta_data: Dict[str, Any]) -> Message:
        assistant_message = Message(chat_id=chat_id, role="assistant", content=content, meta_data=meta_data)
        self.db.add(assistant_message)
        await self.db.commit()
        await self.db.refresh(assistant_message)
        return assistant_message

    async def update_chat_title_if_new(self, chat_id: int, user_content: str, assistant_content: str):
        try:
            result = await self.db.execute(select(Chat).where(Chat.id == chat_id))
            chat = result.scalar_one_or_none()

            if chat and chat.title == "New Chat":
                new_title = self._generate_title(user_content)
                if new_title != "New Chat":
                    chat.title = new_title
                    self.db.add(chat)
                    await self.db.commit()
                    logger.info(f"Chat {chat_id}: Auto-renamed to '{new_title}'")
        except Exception as e:
            logger.error(f"Error auto-renaming chat: {e}")

    def _generate_title(self, user_content: str) -> str:
        clean_content = (user_content or "").split("\n")[0].strip()
        words = clean_content.split()
        title = " ".join(words[:6])
        if title and title[-1] in ".,:;!?":
            title = title[:-1]
        if len(title) > 40:
            title = title[:37] + "..."
        return title or "New Chat"
