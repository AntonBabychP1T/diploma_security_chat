from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
import time
import json
from app.models.chat import Chat, Message
from app.models.memory import Memory
from app.schemas.chat import ChatCreate, MessageCreate, Attachment
from app.utils.pdf_utils import extract_text_from_base64_pdf
from app.services.pii_service import PIIService
from app.providers import ProviderFactory
from app.services.memory_service import MemoryService
from app.utils.logger import get_logger
from app.core.config import get_settings
from fastapi import BackgroundTasks, Request
import asyncio
import uuid
from typing import AsyncGenerator
from app.core.database import SessionLocal

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

    def _generate_title(self, user_content: str, assistant_content: str) -> str:
        """
        Simple local heuristic to generate a chat title.
        Takes the first few words of the user's message.
        """
        # Clean and truncate
        clean_content = user_content.split('\n')[0].strip() # Take first line
        words = clean_content.split()
        
        # Take first 5-7 words
        title = " ".join(words[:6])
        
        # Remove special chars from end
        if title and title[-1] in ".,:;!?":
            title = title[:-1]
            
        if len(title) > 40:
            title = title[:37] + "..."
            
        return title or "New Chat"

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

    async def send_message(self, chat_id: int, content: str, style: str = "default", provider_name: str = "openai", model: str | None = None, attachments: List[Attachment] | None = None) -> Message:
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
        meta_data = {}
        if attachments:
            # Store metadata about attachments, but not the content (to save DB space)
            meta_data["attachments"] = [{"name": a.name, "type": a.type} for a in attachments]
            
        user_message = Message(chat_id=chat_id, role="user", content=content, meta_data=meta_data)
        self.db.add(user_message)
        await self.db.commit() # Commit to get ID and save state
        
        # 2. Load History
        history = await self.get_chat_history(chat_id)
        
        # 3. Prepare Context & Masking
        context_messages = history[-5:] 
        
        masked_messages = []
        combined_mapping = {}
        
        # Add System Prompt
        system_prompt = self.styles.get(style, self.styles["default"])
        if memory_context:
            formatted = "\n".join([f"- {m}" for m in memory_context])
            system_prompt = f"{system_prompt}\n\nHere is context about the user:\n{formatted}"
        masked_messages.append({"role": "system", "content": system_prompt})

        for i, msg in enumerate(context_messages):
            masked_content, mapping = self.pii_service.mask(msg.content)
            
            # If this is the last message (current user message) and we have attachments
            if i == len(context_messages) - 1 and attachments and msg.role == "user":
                 # Construct multimodal content
                 parts = [{"type": "text", "text": masked_content}]
                 for att in attachments:
                     if att.type == "application/pdf" or att.name.lower().endswith(".pdf"):
                         extracted_text = extract_text_from_base64_pdf(att.content)
                         parts.append({
                             "type": "text", 
                             "text": f"--- Document Content: {att.name} ---\n{extracted_text}\n--- End Document ---"
                         })
                     else:
                         # For now, pass base64 directly in a generic format
                         # The provider adapter will convert to specific format (OpenAI image_url, Gemini blob)
                         parts.append({
                             "type": "image_url" if att.type.startswith("image") else "text", 
                             "image_url": {"url": att.content} if att.type.startswith("image") else None,
                             "text": att.content if not att.type.startswith("image") else None,
                             "mime_type": att.type # Helper for provider
                         })
                 masked_messages.append({"role": msg.role, "content": parts})
            else:
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
        
        # Auto-rename if "New Chat" and early in conversation
        if chat.title == "New Chat":
            # We just added 2 messages (user + assistant)
            # If total messages <= 2 (or slightly more if there were errors), rename
            # But simpler check: just check if title is "New Chat"
             new_title = self._generate_title(content, unmasked_content)
             if new_title != "New Chat":
                 chat.title = new_title
                 self.db.add(chat)
                 await self.db.commit()
                 
        return assistant_message

    async def send_message_stream(
        self,
        chat_id: int,
        content: str,
        style: str = "default",
        provider_name: str = "openai",
        model: str | None = None,

        fastapi_request: Request | None = None,
        background_tasks: BackgroundTasks | None = None,
        attachments: List[Attachment] | None = None
    ) -> AsyncGenerator[str, None]:
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

        # Save user message first
        meta_data = {}
        if attachments:
            meta_data["attachments"] = [{"name": a.name, "type": a.type} for a in attachments]
            
        user_message = Message(chat_id=chat_id, role="user", content=content, meta_data=meta_data)
        self.db.add(user_message)
        await self.db.commit()

        history = await self.get_chat_history(chat_id)
        context_messages = history[-5:] 

        masked_messages = []
        combined_mapping = {}

        system_prompt = self.styles.get(style, self.styles["default"])
        if memory_context:
            formatted = "\n".join([f"- {m}" for m in memory_context])
            system_prompt = f"{system_prompt}\n\nHere is context about the user:\n{formatted}"
        masked_messages.append({"role": "system", "content": system_prompt})

        for i, msg in enumerate(context_messages):
            masked_content, mapping = self.pii_service.mask(msg.content)
            
            if i == len(context_messages) - 1 and attachments and msg.role == "user":
                parts = [{"type": "text", "text": masked_content}]
                for att in attachments:
                     if att.type == "application/pdf" or att.name.lower().endswith(".pdf"):
                         extracted_text = extract_text_from_base64_pdf(att.content)
                         parts.append({
                             "type": "text", 
                             "text": f"--- Document Content: {att.name} ---\n{extracted_text}\n--- End Document ---"
                         })
                     else:
                         parts.append({
                             "type": "image_url" if att.type.startswith("image") else "text", 
                             "image_url": {"url": att.content} if att.type.startswith("image") else None,
                             "text": att.content if not att.type.startswith("image") else None,
                             "mime_type": att.type
                         })
                masked_messages.append({"role": msg.role, "content": parts})
            else:
                masked_messages.append({"role": msg.role, "content": masked_content})
                
            combined_mapping.update(mapping)

        provider = ProviderFactory.get_provider(provider_name)
        stream = await provider.stream_generate(
            masked_messages,
            options={
                "model": model,
                "max_completion_tokens": self.settings.OPENAI_MAX_COMPLETION_TOKENS
            }
        )

        full_chunks: list[str] = []

        async def event_generator():
            nonlocal full_chunks
            try:
                async for chunk in stream:
                    if fastapi_request and await fastapi_request.is_disconnected():
                        await stream.aclose()
                        return

                    delta = chunk.choices[0].delta.content or ""
                    if not delta:
                        continue
                    full_chunks.append(delta)
                    unmasked_delta = self.pii_service.unmask(delta, combined_mapping) if combined_mapping else delta
                    payload = {"delta": unmasked_delta}
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            finally:
                # Closing stream if not already
                try:
                    await stream.aclose()
                except Exception:
                    pass

                full_raw = "".join(full_chunks)
                unmasked_full = self.pii_service.unmask(full_raw, combined_mapping) if combined_mapping else full_raw
                if not unmasked_full.strip():
                    unmasked_full = "Вибачте, не вдалося згенерувати відповідь цього разу."

                end_time = time.time()
                meta_data = {
                    "provider": provider_name,
                    "model": model or getattr(provider, "default_model", ""),
                    "latency": end_time - start_time,
                    "masked_used": len(combined_mapping) > 0,
                    "style": style
                }

                assistant_message = Message(
                    chat_id=chat_id,
                    role="assistant",
                    content=unmasked_full,
                    meta_data=meta_data
                )
                self.db.add(assistant_message)
                await self.db.commit()
                await self.db.refresh(assistant_message)

                # Auto-rename
                if chat.title == "New Chat":
                     new_title = self._generate_title(content, unmasked_full)
                     if new_title != "New Chat":
                         chat.title = new_title
                         self.db.add(chat)
                         await self.db.commit()

                # Run memory update in background
                if self.memory_service:
                    async def run_memory_update():
                        try:
                            dialog_fragment = f"user: {content}\nassistant: {unmasked_full}"
                            async with SessionLocal() as session:
                                mem_service = MemoryService(session, self.user_id)
                                await mem_service.update_store_from_extractor(dialog_fragment)
                        except Exception as e:
                            logger.error(f"Memory extractor error: {e}")

                    asyncio.create_task(run_memory_update())

                # Signal end of stream
                yield f"data: {json.dumps({'done': True})}\n\n"

        return event_generator()

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

    async def send_arena_message(self, chat_id: int, content: str, models: List[str], style: str = "default") -> List[Message]:
        # Verify ownership
        chat = await self.get_chat(chat_id)
        if not chat:
            raise ValueError("Chat not found or access denied")

        # 1. Save User Message
        user_message = Message(chat_id=chat_id, role="user", content=content)
        self.db.add(user_message)
        await self.db.commit()

        # 2. Prepare Context (simplified for arena)
        history = await self.get_chat_history(chat_id)
        context_messages = history[-5:]
        
        masked_messages = []
        combined_mapping = {}
        
        system_prompt = self.styles.get(style, self.styles["default"])
        masked_messages.append({"role": "system", "content": system_prompt})

        for msg in context_messages:
            masked_content, mapping = self.pii_service.mask(msg.content)
            masked_messages.append({"role": msg.role, "content": masked_content})
            combined_mapping.update(mapping)

        # 3. Parallel LLM Calls
        comparison_id = str(uuid.uuid4())
        tasks = []
        
        for model_id in models:
            # Determine provider from model_id (heuristic or explicit map needed)
            # Assuming model_id format "provider-model" or simple mapping
            # For now, simplistic check:
            if "gpt" in model_id:
                provider_name = "openai"
            elif "gemini" in model_id:
                provider_name = "gemini"
            else:
                provider_name = "openai" # Fallback

            provider = ProviderFactory.get_provider(provider_name)
            tasks.append(
                provider.generate(
                    masked_messages,
                    options={
                        "model": model_id,
                        "max_completion_tokens": self.settings.OPENAI_MAX_COMPLETION_TOKENS
                    }
                )
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.info(f"Arena mode: received {len(results)} results from gather")
        
        assistant_messages = []
        for i, res in enumerate(results):
            model_id = models[i]
            logger.info(f"Processing result {i} for model {model_id}: type={type(res)}")
            
            if isinstance(res, Exception):
                logger.error(f"Arena error for {model_id}: {res}")
                content = f"Error generating response from {model_id}"
                meta = {"error": str(res)}
            else:
                raw_content = res.content or ""
                logger.info(f"Model {model_id}: raw_content length = {len(raw_content)}, res.content type = {type(res.content)}")
                content = self.pii_service.unmask(raw_content, combined_mapping) or raw_content
                logger.info(f"Model {model_id}: final content length = {len(content)}")
                meta = res.meta_data or {}
            
            meta.update({
                "comparison_id": comparison_id,
                "model": model_id,
                "is_arena": True,
                "style": style
            })

            msg = Message(
                chat_id=chat_id,
                role="assistant",
                content=content,
                meta_data=meta
            )
            self.db.add(msg)
            assistant_messages.append(msg)

        await self.db.commit()
        for msg in assistant_messages:
            await self.db.refresh(msg)
        
        logger.info(f"Arena mode: returning {len(assistant_messages)} messages")
        for msg in assistant_messages:
            logger.info(f"  - Message ID: {msg.id}, Model: {msg.meta_data.get('model')}, Content length: {len(msg.content)}")
            
        return assistant_messages

    async def vote_message(self, chat_id: int, message_id: int, vote_type: str) -> bool:
        # vote_type: "better", "worse", "tie" (though usually we vote for "better")
        # We might want to mark the 'winner' in a comparison pair.
        
        # Fetch message
        query = select(Message).where(Message.id == message_id, Message.chat_id == chat_id)
        result = await self.db.execute(query)
        message = result.scalar_one_or_none()
        
        if not message:
            return False
            
        # Update metadata
        meta = dict(message.meta_data or {})
        meta["vote"] = vote_type
        message.meta_data = meta
        
        # If it's part of a comparison, we might want to find the sibling and mark it too?
        # For now, just marking the voted message is enough for metrics aggregation.
        
        await self.db.commit()
        return True
