import pytest
from tortoise import Tortoise
from src.services import HistoryService, SettingsService, UserService
from src.database.models import ChatMessage, User


@pytest.fixture(scope="function", autouse=True)
async def init_db():
    config = {
        "connections": {"default": "sqlite://:memory:"},
        "apps": {
            "models": {
                "models": ["src.database.models"],
                "default_connection": "default",
            }
        },
    }
    await Tortoise.init(config=config)
    await Tortoise.generate_schemas()
    yield
    await Tortoise.close_connections()

@pytest.mark.asyncio
async def test_settings_service():
    await SettingsService.set_system_prompt("Test Prompt")
    prompt = await SettingsService.get_system_prompt()
    assert prompt == "Test Prompt"


@pytest.mark.asyncio
async def test_user_service():
    test_user = "test_admin"
    test_pass = "securepass"

    await UserService.create_user(test_user, test_pass, is_superuser=True)
    assert await UserService.verify_superuser(test_user, test_pass) is True
    assert await UserService.verify_superuser(test_user, "wrong") is False


@pytest.mark.asyncio
async def test_history_service():
    chat_id = 12345
    await HistoryService.add_message(chat_id, "user", "Hello")
    await HistoryService.add_message(chat_id, "assistant", "Hi there")

    msgs = await HistoryService.get_last_messages(chat_id, limit=5)
    # Note: get_last_messages returns oldest first
    assert len(msgs) == 2
    assert msgs[0]["content"] == "Hello"
    assert msgs[1]["content"] == "Hi there"

    await HistoryService.clear_history(chat_id)
    msgs = await HistoryService.get_last_messages(chat_id)
    assert len(msgs) == 0

