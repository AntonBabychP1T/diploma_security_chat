import json
import re
import asyncio
from typing import List, Dict, Any, Optional

import openai
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.memory import Memory

settings = get_settings()


EXTRACTOR_PROMPT = """
Ти модуль "пам'ять про користувача".

Твоє завдання:
- читати фрагмент діалогу між користувачем і асистентом;
- знаходити інформацію, яку корисно зберегти як довгострокову пам'ять про користувача;
- знаходити місця, де користувач просить щось "забути" або "більше не враховувати";
- не відповідати на запит користувача, а лише виділити пам'ять.

Зберігай тільки те, що:
- буде корисним в майбутніх розмовах;
- стосується особистих даних користувача, його вподобань, стилю спілкування, довгострокових проєктів і обмежень;
- звучить як те, що користувач хоче бачити врахованим і надалі.

Не зберігай:
- одноразові, короткочасні або випадкові факти, які навряд чи знадобляться;
- зайві подробиці, які не впливають на відповіді.

Категорії пам'яті:
- "profile" — ім'я, роль, місто, мова спілкування, базова інформація про користувача;
- "preference" — що йому подобається / не подобається (жанри, стиль відповідей, формат, тон);
- "project" — його поточні довгострокові задачі та проєкти;
- "constraint" — обмеження, яких треба дотримуватися (мова, стиль, заборони);
- "other" — інша важлива інформація, яка не підпадає під попередні категорії.

Формат виходу — строго JSON такого вигляду:

{
  "memories_to_add": [
    {
      "category": "profile | preference | project | constraint | other",
      "key": "короткий опис ключа, наприклад 'name' або 'favorite_genres'",
      "value": "людський текст, що саме потрібно запам'ятати",
      "confidence": 0.0-1.0
    }
  ],
  "memories_to_forget": [
    {
      "key": "ім'я або короткий опис того, що треба забути",
      "reason": "коротке пояснення (наприклад, 'користувач попросив забути')"
    }
  ]
}

Якщо немає, що додати або забути, поверни пусті масиви.
Не додавай жодного тексту поза JSON.
"""


INJECTOR_PROMPT = """
Ти модуль "вибір релевантної пам'яті".

Твоє завдання:
- отримати поточний запит користувача;
- отримати список збережених про нього пам'ятей;
- вибрати тільки ті пам'яті, які реально допоможуть краще відповісти на цей конкретний запит;
- повернути короткий список релевантних фактів.

Враховуй:
- Пам'ять релевантна, якщо вона прямо стосується поточного запиту.
- Стабільні налаштування (мова, стиль відповіді, формат, обмеження) майже завжди релевантні.
- Не додавай зайві або несуттєві факти.

Формат виходу — строго JSON:

{
  "relevant_memories": [
    "коротке речення або факт про користувача, який треба врахувати"
  ]
}

Якщо немає релевантної пам'яті — поверни пустий масив.
Не додавай текст поза JSON.
"""


class MemoryService:
    def __init__(self, db: AsyncSession, user_id: int):
        self.db = db
        self.user_id = user_id
        self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.extract_model = getattr(settings, "MEMORY_EXTRACT_MODEL", "gpt-5-mini")
        self.inject_model = getattr(settings, "MEMORY_INJECT_MODEL", "gpt-5-mini")
        self.extract_max_tokens = getattr(settings, "MEMORY_EXTRACT_MAX_TOKENS", 10000)
        self.inject_max_tokens = getattr(settings, "MEMORY_INJECT_MAX_TOKENS", 10000)

    async def get_memories(self) -> List[Memory]:
        result = await self.db.execute(
            select(Memory).where(Memory.user_id == self.user_id).order_by(Memory.created_at.desc())
        )
        return result.scalars().all()

    async def add_memory(self, category: str, key: str, value: Any, confidence: float = 0.7) -> Memory:
        """Upsert memory by (user_id, category, key) to avoid duplicates and keep values short."""
        # Normalize value to short string
        if isinstance(value, list):
            value = " ".join([str(v) for v in value])
        if value is None:
            value = ""
        short_value = str(value).strip()
        if len(short_value) > 200:
            short_value = short_value[:197] + "..."

        result = await self.db.execute(
            select(Memory)
            .where(
                Memory.user_id == self.user_id,
                Memory.category == category,
                Memory.key == key
            )
            .order_by(Memory.updated_at.desc())
        )
        existing_list = result.scalars().all()
        existing = existing_list[0] if existing_list else None

        # Clean duplicates if any
        if existing_list and len(existing_list) > 1:
            for dup in existing_list[1:]:
                await self.db.delete(dup)

        if existing:
            existing.value = short_value
            existing.confidence = confidence
            await self.db.commit()
            await self.db.refresh(existing)
            return existing

        mem = Memory(
            user_id=self.user_id,
            category=category,
            key=key,
            value=short_value,
            confidence=confidence
        )
        self.db.add(mem)
        await self.db.commit()
        await self.db.refresh(mem)
        return mem

    async def delete_memory(self, memory_id: int) -> bool:
        result = await self.db.execute(
            select(Memory).where(Memory.id == memory_id, Memory.user_id == self.user_id)
        )
        mem = result.scalar_one_or_none()
        if not mem:
            return False
        await self.db.delete(mem)
        await self.db.commit()
        return True

    async def apply_forget_by_key(self, key: str):
        await self.db.execute(
            delete(Memory).where(Memory.user_id == self.user_id, Memory.key == key)
        )
        await self.db.commit()

    async def run_extractor(self, dialog_fragment: str) -> Dict[str, Any]:
        messages = [
            {"role": "system", "content": EXTRACTOR_PROMPT},
            {
                "role": "user",
                "content": f"Проаналізуй цей фрагмент діалогу та виділи пам'ять про користувача:\n\n<<<DIALOG_START\n{dialog_fragment}\nDIALOG_END>>>"
            }
        ]
        try:
            response = await self.client.chat.completions.create(
                model=self.extract_model,
                messages=messages,
                max_completion_tokens=self.extract_max_tokens,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content or ""
            return self._parse_json(content, default={"memories_to_add": [], "memories_to_forget": []})
        except Exception as e:
            print(f"Memory extractor error: {e}")
            return {"memories_to_add": [], "memories_to_forget": []}

    async def run_injector(self, user_message: str, memories: List[Memory]) -> List[str]:
        if not memories:
            return []
        memory_json = [
            {
                "category": m.category,
                "key": m.key,
                "value": m.value,
                "confidence": m.confidence
            }
            for m in memories
        ]
        messages = [
            {"role": "system", "content": INJECTOR_PROMPT},
            {
                "role": "user",
                "content": f"""Ось поточний запит користувача:

<<<USER_MESSAGE
{user_message}
USER_MESSAGE_END>>>

Ось список збережених пам'ятей (у форматі JSON):

<<<MEMORY_STORE
{json.dumps(memory_json, ensure_ascii=False)}
MEMORY_STORE_END>>>

Вибери релевантні пам'яті для цього запиту."""
            }
        ]
        try:
            response = await self.client.chat.completions.create(
                model=self.inject_model,
                messages=messages,
                max_completion_tokens=self.inject_max_tokens,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content or ""
            data = self._parse_json(content, default={"relevant_memories": []})
            return data.get("relevant_memories", [])
        except Exception as e:
            print(f"Memory injector error: {e}")
            return []

    async def update_store_from_extractor(self, dialog_fragment: str):
        result = await self.run_extractor(dialog_fragment)
        added = 0
        for mem in result.get("memories_to_add", []):
            try:
                await self.add_memory(
                    category=mem.get("category", "other"),
                    key=mem.get("key", "fact"),
                    value=mem.get("value", ""),
                    confidence=float(mem.get("confidence", 0.7))
                )
                added += 1
            except Exception as e:
                print(f"Failed to add memory: {e}")
        for forget in result.get("memories_to_forget", []):
            try:
                key = forget.get("key")
                if key:
                    await self.apply_forget_by_key(key)
            except Exception as e:
                print(f"Failed to forget memory: {e}")
        return added

    def _parse_json(self, text: str, default: Any) -> Any:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            try:
                match = re.search(r"{.*}", text, re.DOTALL)
                if match:
                    return json.loads(match.group(0))
            except Exception:
                pass
        return default
