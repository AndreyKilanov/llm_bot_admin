from config import Settings

def get_tortoise_config() -> dict:
    settings = Settings()
    
    if settings.POSTGRES_HOST:
        db_url = (
            f"postgres://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
            f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
        )
    else:
        db_url = f"sqlite://{settings.DATABASE_PATH}"
    
    return {
        "connections": {"default": db_url},
        "apps": {
            "models": {
                "models": ["src.database.models", "aerich.models"],
                "default_connection": "default",
            }
        },
    }

CONFIG = get_tortoise_config()
