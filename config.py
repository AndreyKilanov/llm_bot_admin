from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram
    BOT_TOKEN: str
    TELEGRAM_PROXY_URL: str | None = None

    # OpenRouter
    OPENROUTER_API_KEY: str
    OPENROUTER_MODEL: str = "google/gemma-2.0-flash-001:free"

    # System prompt
    SYSTEM_PROMPT: str = "You are a helpful assistant. Answer concisely and clearly."

    # History
    HISTORY_SIZE: int = 10

    # Webhook
    WEBHOOK_PATH: str = "/webhook"
    WEBHOOK_SECRET: str = ""
    BASE_WEBHOOK_URL: str = "https://yourdomain.com"
    USE_WEBHOOK: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_PATH: str = "data/bot.db"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "llm_bot"
    POSTGRES_HOST: str | None = None
    POSTGRES_PORT: int = 5432

    # Create superuser: ADMIN_USERNAME / ADMIN_PASSWORD (env, for scripts/create_superuser.py)
    ADMIN_USERNAME: str = ""
    ADMIN_PASSWORD: str = ""

    # Logging
    LOG_FILE_PATH: str = "logs/bot.log"

    # Telegram IDs, которым разрешено /set_prompt (через запятую)
    TELEGRAM_ADMIN_IDS: str = ""
