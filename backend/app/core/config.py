from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    OPENAI_API_KEY: str
    GEMINI_API_KEY: str | None = None
    DATABASE_URL: str = "sqlite+aiosqlite:///./chat.db"
    LOG_LEVEL: str = "INFO"
    MEMORY_EXTRACT_MODEL: str = "gpt-5-mini"
    MEMORY_INJECT_MODEL: str = "gpt-5-mini"
    OPENAI_MAX_COMPLETION_TOKENS: int = 2048
    MEMORY_EXTRACT_MAX_TOKENS: int = 10000
    MEMORY_INJECT_MAX_TOKENS: int = 10000
    AUDIO_TRANSCRIBE_MODEL: str = "gpt-4o-mini-transcribe"
    
    model_config = SettingsConfigDict(env_file=".env")

@lru_cache
def get_settings():
    return Settings()
