import pytest
import asyncio
from tortoise import Tortoise

pytest_plugins = ["tests.fixtures"]

@pytest.fixture(scope="session")
def event_loop():
    """Создает экземпляр цикла событий для всей тестовой сессии."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session", autouse=True)
async def init_db():
    config = {
        "connections": {"default": "sqlite://:memory:"},
        "apps": {"models": {"models": ["src.database.models"], "default_connection": "default"}},
    }
    await Tortoise.init(config=config)
    await Tortoise.generate_schemas()
    yield
    await Tortoise._drop_databases()
    await Tortoise.close_connections()

@pytest.fixture(autouse=True)
async def clear_db():
    from src.database.models import User, Setting, ChatMessage, AllowedChat, LLMConnection, LLMPrompt
    await User.all().delete()
    await Setting.all().delete()
    await ChatMessage.all().delete()
    await AllowedChat.all().delete()
    await LLMPrompt.all().delete()
    await LLMConnection.all().delete()
    yield
