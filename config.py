from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram
    BOT_TOKEN: str = "BOT_TOKEN"
    TELEGRAM_PROXY_URL: str | None = None

    # Discord
    DISCORD_BOT_TOKEN: str | None = None


    # OpenRouter
    OPENROUTER_API_KEY: str = "OPENROUTER_API_KEY"
    OPENROUTER_MODEL: str = "google/gemma-2.0-flash-001:free"

    # System prompt
    SYSTEM_PROMPT: str = "You are a helpful assistant. Answer concisely and clearly."

    # History
    HISTORY_SIZE: int = 10  # Fallback logic if needed, but we will move to dynamic settings


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

    # Стандартные базовые URL для популярных провайдеров (OpenAPI совместимые)
    PROVIDER_DEFAULT_URLS: dict = {
        "openrouter": {"name": "OpenRouter", "url": "https://openrouter.ai/api/v1"},
        "openai": {"name": "OpenAI", "url": "https://api.openai.com/v1"},
        "anthropic": {"name": "Anthropic", "url": "https://api.anthropic.com/v1"},
        "google": {"name": "Google (Gemini)", "url": "https://generativelanguage.googleapis.com"},
        "deepseek": {"name": "DeepSeek", "url": "https://api.deepseek.com/v1"},
        "groq": {"name": "Groq", "url": "https://api.groq.com/openai/v1"},
        "together": {"name": "Together AI", "url": "https://api.together.xyz/v1"},
        "mistral": {"name": "Mistral AI", "url": "https://api.mistral.ai/v1"},
        "xai": {"name": "xAI (Grok)", "url": "https://api.x.ai/v1"},
        "ollama": {"name": "Ollama", "url": "http://localhost:11434"}
    }

settings = Settings()
