import logging
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.chat import Chat
from app.models.memory import Memory
from app.schemas.chat import ChatCreate
from app.services.chat_service import ChatService
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)
settings = get_settings()

IMPORTANT_MEMORY_CATEGORIES = {"constraint", "project", "profile"}
IMPORTANT_MEMORY_KEYS = {
    "deadline",
    "timezone",
    "work_hours",
    "availability",
    "meeting_preferences",
    "communication_style",
    "language",
}


@dataclass
class MemoryChangeNotification:
    should_notify: bool
    title: str
    body: str
    chat_message: str


class MemoryChangeNotifier:
    def __init__(self, db: AsyncSession, user_id: int):
        self.db = db
        self.user_id = user_id

    def evaluate(self, action: str, memory: Optional[Memory]) -> MemoryChangeNotification:
        if memory is None:
            return MemoryChangeNotification(False, "", "", "")

        key_lower = (memory.key or "").strip().lower()
        category_lower = (memory.category or "").strip().lower()
        is_important = category_lower in IMPORTANT_MEMORY_CATEGORIES or key_lower in IMPORTANT_MEMORY_KEYS
        if not is_important:
            return MemoryChangeNotification(False, "", "", "")

        if action == "create":
            action_text = "updated"
            chat_message = (
                f"Memory update: `{memory.key}` ({memory.category}) was updated.\n"
                f"Value: {memory.value}"
            )
        else:
            action_text = "deleted"
            chat_message = f"Memory update: `{memory.key}` ({memory.category}) was deleted."

        title = "Important memory change"
        body = f"{memory.key}: {action_text}"
        return MemoryChangeNotification(True, title, body, chat_message)

    async def notify(self, action: str, memory: Optional[Memory]) -> None:
        decision = self.evaluate(action, memory)
        if not decision.should_notify:
            return

        chat = await self._get_or_create_updates_chat()
        chat_service = ChatService(self.db, self.user_id)
        await chat_service.create_system_message(
            chat_id=chat.id,
            content=decision.chat_message,
            source="memory_updates",
            metadata={"memory_key": memory.key if memory else None, "memory_action": action},
        )

        target_url = f"{settings.FRONTEND_PUBLIC_URL.rstrip('/')}/chats/{chat.id}"
        notification_service = NotificationService(self.db)
        await notification_service.send_notification(
            user_id=self.user_id,
            title=decision.title,
            body=decision.body,
            url=target_url,
        )

    async def _get_or_create_updates_chat(self) -> Chat:
        stmt = select(Chat).where(Chat.user_id == self.user_id, Chat.title == "Assistant Updates")
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        if existing:
            return existing

        chat_service = ChatService(self.db, self.user_id)
        return await chat_service.create_chat(ChatCreate(title="Assistant Updates"))
