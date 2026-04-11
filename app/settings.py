import os


class Settings:
    REDIS_URL: str | None = os.getenv("REDIS_URL")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./cp_assistant.db")
    SESSION_TTL_SECONDS: int = int(os.getenv("SESSION_TTL_SECONDS", "86400"))
    OXLO_BASE_URL: str = os.getenv("OXLO_BASE_URL", "https://api.oxlo.ai/v1")
    OXLO_API_KEY: str | None = os.getenv("OXLO_API_KEY")
    CODEFORCES_PROXY_URL: str | None = os.getenv("CODEFORCES_PROXY_URL")

    MODEL_INTENT_DETECTION: str = os.getenv("MODEL_INTENT_DETECTION", "Llama 3.2 3B")
    MODEL_HINT_AGENT: str = os.getenv("MODEL_HINT_AGENT", "Llama 3.1 8B")
    MODEL_CODE_ANALYZER: str = os.getenv("MODEL_CODE_ANALYZER", "Qwen 3 Coder 30B")
    MODEL_STRATEGY_AGENT: str = os.getenv("MODEL_STRATEGY_AGENT", "DeepSeek R1 8B")
    MODEL_APPROACH_DETECTOR: str = os.getenv("MODEL_APPROACH_DETECTOR", "DeepSeek R1 8B")
    MODEL_APPROACH_VALIDATOR: str = os.getenv("MODEL_APPROACH_VALIDATOR", "DeepSeek R1 8B")
    MODEL_COUNTEREXAMPLE_GEN: str = os.getenv("MODEL_COUNTEREXAMPLE_GEN", "DeepSeek R1 8B")
    MODEL_GENERAL_CHAT: str = os.getenv("MODEL_GENERAL_CHAT", "Mistral 7B")


settings = Settings()
