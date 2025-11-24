from typing import List, Dict, Any, Optional
import openai
from app.core.config import get_settings
from .base import LLMProvider, ProviderResponse

settings = get_settings()

class OpenAIProvider(LLMProvider):
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        # Сучасна модель
        self.default_model = "gpt-5-nano"

    async def generate(
        self,
        messages: List[Dict[str, str]],
        options: Optional[Dict[str, Any]] = None
    ) -> ProviderResponse:
        options = options or {}

        model = options.get("model", self.default_model)
        
        # Model-specific constraints
        default_max = options.get("max_completion_tokens") or settings.OPENAI_MAX_COMPLETION_TOKENS
        if model in {"gpt-5-nano", "gpt-5-mini", "gpt-5.1"}:
            # Avoid sending unsupported temperature for these models
            temperature = None
            max_completion_tokens = default_max
        else:
            temperature = options.get("temperature", None)
            max_completion_tokens = default_max

        try:
            # Prepare arguments
            kwargs = {
                "model": model,
                "messages": messages,
                "max_completion_tokens": max_completion_tokens
            }
            
            if temperature is not None:
                kwargs["temperature"] = temperature

            response = await self.client.chat.completions.create(**kwargs)

            content = response.choices[0].message.content
            usage = response.usage.model_dump() if response.usage else {}

            return ProviderResponse(
                content=content,
                meta_data={
                    "provider": "openai",
                    "model": model,
                    "usage": usage,
                    "finish_reason": response.choices[0].finish_reason,
                },
            )
        except Exception as e:
            # Retry once without temperature if the error is about unsupported temperature value
            err_text = str(e)
            if "temperature" in err_text:
                try:
                    kwargs.pop("temperature", None)
                    response = await self.client.chat.completions.create(**kwargs)
                    content = response.choices[0].message.content
                    usage = response.usage.model_dump() if response.usage else {}
                    return ProviderResponse(
                        content=content,
                        meta_data={
                            "provider": "openai",
                            "model": model,
                            "usage": usage,
                            "finish_reason": response.choices[0].finish_reason,
                        },
                    )
                except Exception as inner:
                    print(f"OpenAI Provider Error after retry: {inner}")
                    raise inner
            print(f"OpenAI Provider Error: {e}")
            raise e
