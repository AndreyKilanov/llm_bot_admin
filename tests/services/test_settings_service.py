import pytest
from tortoise import Tortoise
from src.services.settings_service import SettingsService
from src.database.models import Setting
from config import Settings


@pytest.mark.asyncio
async def test_get_system_prompt_default():
    prompt = await SettingsService.get_system_prompt()
    assert prompt == Settings().SYSTEM_PROMPT

@pytest.mark.asyncio
async def test_set_and_get_system_prompt():
    await SettingsService.set_system_prompt("New system prompt")
    prompt = await SettingsService.get_system_prompt()
    assert prompt == "New system prompt"
    
    # Check update
    await SettingsService.set_system_prompt("Updated prompt")
    assert await SettingsService.get_system_prompt() == "Updated prompt"

@pytest.mark.asyncio
async def test_is_discord_music_enabled_default():
    assert await SettingsService.is_discord_music_enabled() is True

@pytest.mark.asyncio
async def test_is_discord_music_enabled_custom():
    await Setting.create(key="discord_music_enabled", value="false")
    assert await SettingsService.is_discord_music_enabled() is False

    await Setting.filter(key="discord_music_enabled").update(value="TrUe")
    assert await SettingsService.is_discord_music_enabled() is True

@pytest.mark.asyncio
async def test_get_discord_seek_time_default():
    assert await SettingsService.get_discord_seek_time() == 10

@pytest.mark.asyncio
async def test_get_discord_seek_time_custom():
    await Setting.create(key="discord_seek_time", value="15")
    assert await SettingsService.get_discord_seek_time() == 15

@pytest.mark.asyncio
async def test_get_discord_seek_time_invalid():
    await Setting.create(key="discord_seek_time", value="abc")
    assert await SettingsService.get_discord_seek_time() == 10
