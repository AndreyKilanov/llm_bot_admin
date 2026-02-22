import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram.enums import ChatType
from tortoise import Tortoise

from src.bot.telegram.middleware import WhitelistMiddleware
from src.database.models import AllowedChat, Setting



@pytest.mark.asyncio
async def test_whitelist_private_chat_allowed_default():
    middleware = WhitelistMiddleware()
    handler = AsyncMock(return_value="OK")
    
    event = MagicMock()
    event.chat.type = ChatType.PRIVATE
    event.chat.id = 123
    
    result = await middleware(handler, event, {})
    assert result == "OK"
    handler.assert_called_once()

@pytest.mark.asyncio
async def test_whitelist_private_chat_disabled():
    # Disable private chats
    await Setting.create(key="allow_private_chat", value="False")
    
    middleware = WhitelistMiddleware()
    handler = AsyncMock(return_value="OK")
    
    event = MagicMock()
    event.chat.type = ChatType.PRIVATE
    event.chat.id = 123
    
    result = await middleware(handler, event, {})
    assert result is None
    handler.assert_not_called()

@pytest.mark.asyncio
async def test_whitelist_group_allowed():
    # Setup
    chat_id = -100123456789
    await AllowedChat.create(chat_id=chat_id, title="Allowed Group")

    middleware = WhitelistMiddleware()
    handler = AsyncMock(return_value="OK")
    
    event = MagicMock()
    event.chat.type = ChatType.GROUP
    event.chat.id = chat_id
    event.chat.title = "Allowed Group"
    
    result = await middleware(handler, event, {})
    assert result == "OK"
    handler.assert_called_once()

@pytest.mark.asyncio
async def test_whitelist_group_not_allowed():
    # Disable new chats to trigger whitelist check for groups
    await Setting.create(key="telegram_allow_new_chats", value="False")
    
    chat_id = -100987654321
    
    middleware = WhitelistMiddleware()
    handler = AsyncMock(return_value="OK")
    
    event = MagicMock()
    event.chat.type = ChatType.SUPERGROUP
    event.chat.id = chat_id
    event.chat.title = "Not Allowed Group"
    
    result = await middleware(handler, event, {})
    assert result is None
    handler.assert_not_called()

@pytest.mark.asyncio
async def test_whitelist_group_inactive():
    chat_id = -100555555555
    await AllowedChat.create(chat_id=chat_id, title="Inactive Group", is_active=False)
    
    middleware = WhitelistMiddleware()
    handler = AsyncMock(return_value="OK")
    
    event = MagicMock()
    event.chat.type = ChatType.GROUP
    event.chat.id = chat_id
    
    result = await middleware(handler, event, {})
    assert result is None
    handler.assert_not_called()
