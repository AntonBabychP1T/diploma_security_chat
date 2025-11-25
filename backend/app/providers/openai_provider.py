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
        configured_max = options.get("max_completion_tokens") or settings.OPENAI_MAX_COMPLETION_TOKENS
        # Hard cap to avoid long generations that hurt latency
        default_max = min(configured_max, 2048)
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
            if "response_format" in options:
                kwargs["response_format"] = options["response_format"]
            
            if "tools" in options:
                kwargs["tools"] = options["tools"]
            if "tool_choice" in options:
                kwargs["tool_choice"] = options["tool_choice"]
            
            if temperature is not None:
                kwargs["temperature"] = temperature

            response = await self.client.chat.completions.create(**kwargs)

            message = response.choices[0].message
            content = message.content
            tool_calls = message.tool_calls if hasattr(message, "tool_calls") else None
            
            usage = response.usage.model_dump() if response.usage else {}

            meta_data = {
                "provider": "openai",
                "model": model,
                "usage": usage,
                "finish_reason": response.choices[0].finish_reason,
            }
            
            if tool_calls:
                meta_data["tool_calls"] = [t.model_dump() for t in tool_calls]

            return ProviderResponse(
                content=content,
                tool_calls=tool_calls, # Ensure ProviderResponse supports this or add to meta_data if strictly typed
                meta_data=meta_data,
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

    async def stream_generate(
        self,
        messages: List[Dict[str, str]],
        options: Optional[Dict[str, Any]] = None
    ):
        options = options or {}
        model = options.get("model", self.default_model)

        configured_max = options.get("max_completion_tokens") or settings.OPENAI_MAX_COMPLETION_TOKENS
        default_max = min(configured_max, 2048)
        if model in {"gpt-5-nano", "gpt-5-mini", "gpt-5.1"}:
            temperature = None
            max_completion_tokens = default_max
        else:
            temperature = options.get("temperature", None)
            max_completion_tokens = default_max

        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_completion_tokens": max_completion_tokens,
            "stream": True
        }
        if temperature is not None:
            kwargs["temperature"] = temperature

        try:
            return await self.client.chat.completions.create(**kwargs)
        except Exception as e:
            err_text = str(e)
            if "temperature" in err_text:
                try:
                    kwargs.pop("temperature", None)
                    return await self.client.chat.completions.create(**kwargs)
                except Exception as inner:
                    print(f"OpenAI Stream Error after retry: {inner}")
                    raise inner
            print(f"OpenAI Stream Error: {e}")
            raise e
