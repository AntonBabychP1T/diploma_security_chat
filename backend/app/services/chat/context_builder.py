from __future__ import annotations

from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.chat import Message
from app.models.memory import Memory
from app.services.memory_service import MemoryService
from app.utils.logger import get_logger
import time

logger = get_logger("context_builder")


class ContextBuilder:
    def __init__(self, db: AsyncSession, user_id: Optional[int]):
        self.db = db
        self.user_id = user_id
        self.memory_service = MemoryService(db, user_id) if user_id else None
        self.styles = {
            "default": "You are a helpful assistant.",
            "professional": "You are a professional consultant. Provide detailed, formal, and accurate responses.",
            "friendly": "You are a friendly and casual assistant. Use emojis and a relaxed tone.",
            "concise": "You are a concise assistant. Answer briefly and directly.",
        }

    async def build_context(self, chat_id: int, style: str = "default", history_limit: int = 50, max_chars: int = 40000) -> Tuple[str, List[Message]]:
        """
        Returns:
          - system_prompt: str
          - recent_history: List[Message] (DB objects)
        """
        start_time = time.time()

        history = await self._get_chat_history(chat_id)
        
        # 1. First limit by count (soft limit)
        recent_history = history[-history_limit:]
        
        # 2. Then limit by chars (hard budget)
        recent_history = self._trim_history(recent_history, max_chars)

        memory_context: list[str] = []
        if self.memory_service:
            try:
                # We can fetch memories related to the *recent* content
                last_content = recent_history[-1].content if recent_history else ""
                stored_memories = await self.memory_service.get_memories()
                # Ideally retrieve_context(last_content) but keeping existing logic for safety
                # Using existing _select_relevant_memories which filters generic dump
                memory_context = self._select_relevant_memories(stored_memories)
            except Exception as e:
                logger.error(f"Memory context build error: {e}")

        base_prompt = self.styles.get(style, self.styles["default"])
        if memory_context:
            formatted_memories = "\n".join([f"- {m}" for m in memory_context])
            system_prompt = f"{base_prompt}\n\nHere is context about the user:\n{formatted_memories}"
        else:
            system_prompt = base_prompt

        logger.info(f"Context build took {time.time() - start_time:.4f}s. History: {len(recent_history)} items.")
        return system_prompt, recent_history

    def _trim_history(self, history: List[Message], max_chars: int) -> List[Message]:
        if not history:
            return []
        
        total_chars = 0
        trimmed = []
        # Traverse from end to start to keep most recent
        for msg in reversed(history):
            content = msg.content or ""
            c_len = len(content)
            
            # Simple heuristic: if adding this message exceeds budget, we stop
            if total_chars + c_len > max_chars:
                break
            
            trimmed.append(msg)
            total_chars += c_len
            
        return list(reversed(trimmed))

    async def _get_chat_history(self, chat_id: int) -> List[Message]:
        query = select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at.asc())
        result = await self.db.execute(query)
        return result.scalars().all()

    def _select_relevant_memories(self, memories: list[Memory]) -> list[str]:
        if not memories:
            return []

        dedup: dict[tuple[str, str], Memory] = {}
        for m in memories:
            if (m.confidence or 0) < 0.75:
                continue
            k = (m.category, m.key)
            if k not in dedup:
                dedup[k] = m
                continue
            existing = dedup[k]
            if (m.confidence or 0) > (existing.confidence or 0) or (
                (m.confidence or 0) == (existing.confidence or 0) and (m.updated_at or m.created_at) > (existing.updated_at or existing.created_at)
            ):
                dedup[k] = m

        items = list(dedup.values())

        def sort_key(mm: Memory):
            return (-(mm.confidence or 0), mm.updated_at or mm.created_at)

        categories = ["constraint", "profile", "preference", "project", "other"]
        selected: list[Memory] = []

        for cat in categories:
            subset = [m for m in items if m.category == cat or (cat == "constraint" and "language" in (m.key or "").lower())]
            subset.sort(key=sort_key)
            limit = 5 if cat in ["constraint", "profile"] else (4 if cat == "preference" else (3 if cat == "project" else 2))
            selected.extend(subset[:limit])

        sentences: list[str] = []
        for m in selected[:15]:
            value = (m.value or "").strip()
            if len(value) > 120:
                value = value[:117] + "..."
            if value:
                sentences.append(value)
        return sentences
