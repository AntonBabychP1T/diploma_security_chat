from .base import LLMProvider, ProviderResponse
from .openai_provider import OpenAIProvider
from .gemini_provider import GeminiProvider

class ProviderFactory:
    _providers = {
        "openai": OpenAIProvider,
        "gemini": GeminiProvider
    }
    _instances = {}

    @classmethod
    def get_provider(cls, name: str) -> LLMProvider:
        if name not in cls._instances:
            provider_class = cls._providers.get(name)
            if not provider_class:
                raise ValueError(f"Provider {name} not found")
            cls._instances[name] = provider_class()
        return cls._instances[name]

    @classmethod
    def register_provider(cls, name: str, provider_class):
        cls._providers[name] = provider_class

