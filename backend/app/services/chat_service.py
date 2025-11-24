from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
import time
from app.models.chat import Chat, Message
from app.models.memory import Memory
from app.schemas.chat import ChatCreate, MessageCreate
from app.services.pii_service import PIIService
from app.providers import ProviderFactory
from app.services.memory_service import MemoryService
from app.utils.logger import get_logger
from app.core.config import get_settings

logger = get_logger("chat_service")

class ChatService:
    def __init__(self, db: AsyncSession, user_id: Optional[int] = None):
        self.db = db
        self.user_id = user_id
        self.pii_service = PIIService()
        self.provider_factory = ProviderFactory()
        self.styles = {
            "default": "You are a helpful assistant.",
            "professional": "You are a professional consultant. Provide detailed, formal, and accurate responses.",
            "friendly": "You are a friendly and casual assistant. Use emojis and a relaxed tone.",
            "concise": "You are a concise assistant. Answer briefly and directly."
        }
        self.memory_service = MemoryService(db, user_id) if user_id else None
        self.settings = get_settings()

    async def create_chat(self, chat_data: ChatCreate) -> Chat:
        logger.info(f"Creating chat with title: {chat_data.title} for user_id: {self.user_id}")
        new_chat = Chat(title=chat_data.title, user_id=self.user_id)
        self.db.add(new_chat)
        try:
            await self.db.commit()
            await self.db.commit()
            # Refresh with messages loaded
            query = select(Chat).options(selectinload(Chat.messages)).where(Chat.id == new_chat.id)
            result = await self.db.execute(query)
            refreshed_chat = result.scalar_one()
            logger.info(f"Chat created with ID: {refreshed_chat.id}")
            return refreshed_chat
        except Exception as e:
            logger.error(f"Error saving chat to DB: {e}")
            raise e

    async def get_chats(self) -> List[Chat]:
        query = select(Chat).options(selectinload(Chat.messages)).order_by(Chat.updated_at.desc())
        if self.user_id:
            query = query.where(Chat.user_id == self.user_id)
            
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_chat(self, chat_id: int) -> Optional[Chat]:
        query = select(Chat).options(selectinload(Chat.messages)).where(Chat.id == chat_id)
        if self.user_id:
            query = query.where(Chat.user_id == self.user_id)
            
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_chat(self, chat_id: int, chat_data: ChatCreate) -> Optional[Chat]:
        chat = await self.get_chat(chat_id)
        if chat:
            chat.title = chat_data.title
            await self.db.commit()
            await self.db.refresh(chat)
        return chat

    async def delete_chat(self, chat_id: int) -> bool:
        chat = await self.get_chat(chat_id)
        if chat:
            await self.db.delete(chat)
            await self.db.commit()
            return True
        return False

    async def get_chat_history(self, chat_id: int) -> List[Message]:
        # Ensure user owns chat first
        chat = await self.get_chat(chat_id)
        if not chat:
            return []
            
        result = await self.db.execute(
            select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at.asc())
        )
        return result.scalars().all()

    async def send_message(self, chat_id: int, content: str, style: str = "default", provider_name: str = "openai", model: str | None = None) -> Message:
        # Verify ownership
        chat = await self.get_chat(chat_id)
        if not chat:
            raise ValueError("Chat not found or access denied")

        start_time = time.time()
        memory_context: list[str] = []
        if self.memory_service:
            try:
                stored_memories = await self.memory_service.get_memories()
                memory_context = self.build_relevant_memory_context(stored_memories)
            except Exception as e:
                logger.error(f"Memory context build error: {e}")
        
        # 1. Save User Message (Original)
        user_message = Message(chat_id=chat_id, role="user", content=content)
        self.db.add(user_message)
        await self.db.commit() # Commit to get ID and save state
        
        # 2. Load History
        history = await self.get_chat_history(chat_id)
        
        # 3. Prepare Context & Masking
        context_messages = history[-10:] 
        
        masked_messages = []
        combined_mapping = {}
        
        # Add System Prompt
        system_prompt = self.styles.get(style, self.styles["default"])
        if memory_context:
            formatted = "\n".join([f"- {m}" for m in memory_context])
            system_prompt = f"{system_prompt}\n\nHere is context about the user:\n{formatted}"
        masked_messages.append({"role": "system", "content": system_prompt})

        for msg in context_messages:
            masked_content, mapping = self.pii_service.mask(msg.content)
            masked_messages.append({"role": msg.role, "content": masked_content})
            combined_mapping.update(mapping) # Merge mappings
            
        # 4. Call LLM
        provider = ProviderFactory.get_provider(provider_name)
        try:
            llm_response = await provider.generate(
                masked_messages,
                options={
                    "model": model,
                    "max_completion_tokens": self.settings.OPENAI_MAX_COMPLETION_TOKENS
                }
            )
        except Exception as e:
            logger.error(f"LLM Error: {e}")
            raise e

        # 5. Unmask Response
        raw_content = llm_response.content or ""
        unmasked_content = self.pii_service.unmask(raw_content, combined_mapping) or raw_content
        if not unmasked_content.strip():
            unmasked_content = "Вибачте, не вдалося згенерувати відповідь цього разу."
        
        end_time = time.time()
        latency = end_time - start_time
        
        # 6. Save Assistant Response
        meta_data = llm_response.meta_data or {}
        meta_data.update({
            "latency": latency,
            "masked_used": len(combined_mapping) > 0,
            "style": style
        })
        
        assistant_message = Message(
            chat_id=chat_id,
            role="assistant",
            content=unmasked_content,
            meta_data=meta_data
        )
        self.db.add(assistant_message)
        await self.db.commit()
        await self.db.refresh(assistant_message)

        logger.info(f"Chat {chat_id}: Processed message. Latency: {latency:.2f}s. Masked: {meta_data['masked_used']}")
        
        return assistant_message

    def build_relevant_memory_context(self, memories: list[Memory]) -> list[str]:
        """Lightweight heuristic selector to avoid LLM calls in the critical path."""
        if not memories:
            return []

        # Deduplicate by (category, key) keeping highest confidence then latest update
        dedup: dict[tuple[str, str], Memory] = {}
        for m in memories:
            if m.confidence < 0.75:
                continue
            k = (m.category, m.key)
            if k not in dedup:
                dedup[k] = m
                continue
            existing = dedup[k]
            if m.confidence > existing.confidence or (m.confidence == existing.confidence and m.updated_at > existing.updated_at):
                dedup[k] = m

        items = list(dedup.values())

        # Prioritize constraints and language/style
        constraint = [m for m in items if m.category == "constraint" or "language" in m.key.lower()]
        profile = [m for m in items if m.category == "profile"]
        preference = [m for m in items if m.category == "preference"]
        project = [m for m in items if m.category == "project"]
        other = [m for m in items if m.category == "other"]

        def sort_key(m: Memory):
            return (-(m.confidence or 0), m.updated_at or m.created_at)

        constraint.sort(key=sort_key)
        profile.sort(key=sort_key)
        preference.sort(key=sort_key)
        project.sort(key=sort_key)
        other.sort(key=sort_key)

        selected: list[Memory] = []
        selected.extend(constraint[:5])
        selected.extend(profile[:5])
        selected.extend(preference[:4])
        selected.extend(project[:3])
        selected.extend(other[:2])

        sentences = []
        for m in selected[:15]:
            value = m.value.strip()
            # Keep it short
            if len(value) > 120:
                value = value[:117] + "..."
            sentences.append(value)
        return sentences
