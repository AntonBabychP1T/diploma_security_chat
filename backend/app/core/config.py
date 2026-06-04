from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    OPENAI_API_KEY: str
    GEMINI_API_KEY: str | None = None
    DATABASE_URL: str = "sqlite+aiosqlite:///./chat.db"
    LOG_LEVEL: str = "INFO"
    OPENAI_DEFAULT_MODEL: str = "gpt-5.5"
    OPENAI_REASONING_EFFORT: str | None = "medium"
    OPENAI_TEXT_VERBOSITY: str | None = "medium"
    MEMORY_EXTRACT_MODEL: str = "gpt-5.4-mini"
    MEMORY_INJECT_MODEL: str = "gpt-5.4-mini"
    SECRETARY_MODEL: str = "gpt-5.4-mini"
    SECRETARY_MAX_TURNS: int = 5
    OPENAI_MAX_COMPLETION_TOKENS: int = 2048
    MEMORY_EXTRACT_MAX_TOKENS: int = 10000
    MEMORY_INJECT_MAX_TOKENS: int = 10000
    AUDIO_TRANSCRIBE_MODEL: str = "gpt-4o-mini-transcribe"
    FRONTEND_PUBLIC_URL: str = "https://tender-terrapin-bold.ngrok-free.app"
    
    # Google OAuth
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    GOOGLE_REDIRECT_URI: str | None = None

    # Microsoft OAuth
    MICROSOFT_CLIENT_ID: str | None = None
    MICROSOFT_CLIENT_SECRET: str | None = None
    MICROSOFT_REDIRECT_URI: str | None = None
    MICROSOFT_TENANT_ID: str = "common"

    # Web Push
    VAPID_PRIVATE_KEY: str | None = None
    VAPID_PUBLIC_KEY: str | None = None
    VAPID_CLAIM_EMAIL: str | None = None

    # Scheduler / digest automation
    SCHEDULER_TIMEZONE: str = "Europe/Kyiv"
    POLL_INTERVAL_MINUTES: int = 60
    MORNING_DIGEST_HOUR: int = 9
    MORNING_DIGEST_MINUTE: int = 0
    EVENING_DIGEST_HOUR: int = 19
    EVENING_DIGEST_MINUTE: int = 0

    # PII engine flags
    PII_V2_ENABLED: bool = True
    PII_TOKEN_FORMAT: str = "v2"
    PII_CONTEXTUAL_NUMERIC_IDS: bool = True
    PII_STREAM_BUFFERING: bool = True

    model_config = SettingsConfigDict(env_file=".env")

@lru_cache
def get_settings():
    return Settings()
