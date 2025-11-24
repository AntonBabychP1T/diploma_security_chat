import asyncio
from typing import List, Dict, Any, Optional
import google.generativeai as genai

from app.core.config import get_settings
from .base import LLMProvider, ProviderResponse

settings = get_settings()

class GeminiProvider(LLMProvider):
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not configured")
        # Google client picks v1beta internally; model names must match API version
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.default_model = "gemini-2.5-flash"

    async def generate(
        self,
        messages: List[Dict[str, str]],
        options: Optional[Dict[str, Any]] = None
    ) -> ProviderResponse:
        options = options or {}
        model_name = options.get("model", self.default_model)

        # Flatten chat messages into a simple prompt for Gemini
        prompt = "\n".join([f"{m.get('role', 'user').capitalize()}: {m.get('content', '')}" for m in messages])

        # Normalize model name to full "models/..." path; allow simple aliases
        alias_map = {
            "gemini-2.5-flash": "models/gemini-2.5-flash",
            "gemini-2.5-flash-lite": "models/gemini-2.5-flash-lite",
        }
        model_id = alias_map.get(model_name, model_name)
        if not model_id.startswith("models/"):
            model_id = f"models/{model_id}"

        def _generate_sync():
            model = genai.GenerativeModel(model_id)
            return model.generate_content(prompt)

        try:
            response = await asyncio.to_thread(_generate_sync)
            text = response.text or ""
            usage = getattr(response, "usage_metadata", None)
            usage_data = {}
            if usage:
                usage_data = {
                    "prompt_token_count": getattr(usage, "prompt_token_count", None),
                    "candidates_token_count": getattr(usage, "candidates_token_count", None),
                    "total_token_count": getattr(usage, "total_token_count", None),
                }

            return ProviderResponse(
                content=text,
                meta_data={
                    "provider": "gemini",
                    "model": model_name,
                    "usage": usage_data
                }
            )
        except Exception as e:
            print(f"Gemini Provider Error: {e}")
            raise e
