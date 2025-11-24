from .base import LLMProvider
from .openai_provider import OpenAIProvider
from .gemini_provider import GeminiProvider

class ProviderFactory:
    _providers = {
        "openai": OpenAIProvider,
        "gemini": GeminiProvider
    }

    @classmethod
    def get_provider(cls, name: str) -> LLMProvider:
        provider_class = cls._providers.get(name)
        if not provider_class:
            raise ValueError(f"Provider {name} not found")
        return provider_class()

    @classmethod
    def register_provider(cls, name: str, provider_class):
        cls._providers[name] = provider_class
