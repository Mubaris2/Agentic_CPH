import os


class Settings:
    REDIS_URL: str | None = os.getenv("REDIS_URL")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./cp_assistant.db")
    SESSION_TTL_SECONDS: int = int(os.getenv("SESSION_TTL_SECONDS", "86400"))


settings = Settings()
