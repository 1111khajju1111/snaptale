from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
import os

DEFAULT_INSECURE_KEY = "snaptale-super-secret-production-key-change-me"

class Settings(BaseSettings):
    APP_NAME: str = "SnapTale"
    APP_ENV: str = "development"
    PORT: int = 8000
    
    # Database
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./snaptale.db",
        description="Aiven PostgreSQL or local SQLite URL"
    )
    
    # Supabase Auth & Storage
    SUPABASE_URL: str = "https://mock.supabase.co"
    SUPABASE_ANON_KEY: str = "mock-anon-key"
    SUPABASE_SERVICE_ROLE_KEY: str = "mock-service-role-key"
    SUPABASE_JWT_SECRET: str = ""
    STORAGE_BUCKET: str = "snaptale-media"
    
    # AI Engine
    AI_PROVIDER: str = "mock"  # "mock", "huggingface", "gemini"
    AI_PROVIDER_API_KEY: str = ""
    HF_TOKEN: str = ""
    HF_PROVIDER: str = "auto"
    HF_TEXT_MODEL: str = "openai/gpt-oss-20b"
    HF_VISION_MODEL: str = "Qwen/Qwen2.5-VL-3B-Instruct"
    HF_IMAGE_MODEL: str = "black-forest-labs/FLUX.1-schnell"
    GEMINI_API_KEY: str = ""
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Security
    JWT_SECRET_KEY: str = DEFAULT_INSECURE_KEY
    JWT_ALGORITHM: str = "HS256"
    PIN_MAX_ATTEMPTS: int = 5
    PIN_LOCKOUT_MINUTES: int = 15
    SNAPPLUS_SESSION_MINUTES: int = 15
    
    # CORS (Configured origins)
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8080,https://snaptale.vercel.app"
    
    # Quotas (MVP Cost Control)
    MAX_STORIES_PER_DAY: int = 3
    MAX_MUTATIONS_PER_DAY: int = 5
    MAX_REMIXES_PER_DAY: int = 5
    MAX_CHATS_PER_DAY: int = 50
    MAX_PINNED_PER_CATEGORY: int = 10

    @property
    def cors_origins_list(self) -> List[str]:
        if self.CORS_ORIGINS == "*":
            if self.APP_ENV == "production":
                raise RuntimeError("Wildcard CORS (*) is not permitted in production environment.")
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    def validate_production_security(self):
        """Strict check to ensure production cannot start with insecure defaults."""
        if self.APP_ENV == "production":
            if not self.JWT_SECRET_KEY or self.JWT_SECRET_KEY == DEFAULT_INSECURE_KEY:
                raise RuntimeError(
                    "FATAL CONFIG ERROR: Production deployment requires a secure, non-default JWT_SECRET_KEY."
                )
            if self.CORS_ORIGINS == "*":
                raise RuntimeError(
                    "FATAL CONFIG ERROR: Production deployment cannot use wildcard CORS (*)."
                )

            # AI provider gate: production must never silently run on mock vision,
            # story, image, or moderation providers (e.g. filename-based "human
            # detection", fixed placeholder images, or a blocklist moderator).
            provider_type = self.AI_PROVIDER.lower()
            if provider_type == "mock":
                raise RuntimeError(
                    "FATAL CONFIG ERROR: Production deployment cannot run with AI_PROVIDER=mock. "
                    "Set AI_PROVIDER=huggingface with a valid HF_TOKEN (or configure another real provider)."
                )
            if provider_type == "huggingface" and not (self.HF_TOKEN or self.AI_PROVIDER_API_KEY):
                raise RuntimeError(
                    "FATAL CONFIG ERROR: Production deployment has AI_PROVIDER=huggingface but no "
                    "HF_TOKEN/AI_PROVIDER_API_KEY configured."
                )
            if provider_type == "gemini" and not (self.GEMINI_API_KEY or self.AI_PROVIDER_API_KEY):
                raise RuntimeError(
                    "FATAL CONFIG ERROR: Production deployment has AI_PROVIDER=gemini but no "
                    "GEMINI_API_KEY/AI_PROVIDER_API_KEY configured. Refusing to start on mock fallback."
                )

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
settings.validate_production_security()