import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from aiogram.types import Message, User, Chat

from src.bot.telegram.middleware import LoggingMiddleware, WhitelistMiddleware


@pytest.mark.asyncio
async def test_logging_middleware(mock_tg_message):
    middleware = LoggingMiddleware()
    handler = AsyncMock(return_value="handled")
    data = {"test": "data"}

    with patch("src.bot.telegram.middleware.logger") as mock_logger:
        result = await middleware(handler, mock_tg_message, data)
        assert result == "handled"
        mock_logger.info.assert_called_once()
        handler.assert_called_once_with(mock_tg_message, data)


@pytest.mark.asyncio
async def test_whitelist_middleware_bot_disabled(mock_tg_message):
    middleware = WhitelistMiddleware()
    handler = AsyncMock(return_value="handled")
    
    with patch("src.bot.telegram.middleware.Setting.get_or_none", new_callable=AsyncMock) as mock_setting:
        mock_setting.return_value = MagicMock(value="False")
        
        result = await middleware(handler, mock_tg_message, {})
        assert result is None
        handler.assert_not_called()


@pytest.mark.asyncio
async def test_whitelist_middleware_chat_allowed(mock_tg_message):
    middleware = WhitelistMiddleware()
    handler = AsyncMock(return_value="handled")
    
    with patch("src.bot.telegram.middleware.Setting.get_or_none", new_callable=AsyncMock) as mock_setting, \
         patch("src.bot.telegram.middleware.AllowedChat.get_or_none", new_callable=AsyncMock) as mock_allowed:
        
        # Bot is enabled
        mock_setting.return_value = MagicMock(value="True")
        
        # Chat is allowed and active
        mock_allowed.return_value = MagicMock(is_active=True)
        
        result = await middleware(handler, mock_tg_message, {})
        assert result == "handled"
        handler.assert_called_once()


@pytest.mark.asyncio
async def test_whitelist_middleware_chat_disallowed_explicitly(mock_tg_message):
    middleware = WhitelistMiddleware()
    handler = AsyncMock(return_value="handled")
    
    with patch("src.bot.telegram.middleware.Setting.get_or_none", new_callable=AsyncMock) as mock_setting, \
         patch("src.bot.telegram.middleware.AllowedChat.get_or_none", new_callable=AsyncMock) as mock_allowed:
        
        mock_setting.return_value = MagicMock(value="True")
        
        # Chat is allowed but NOT active
        mock_allowed.return_value = MagicMock(is_active=False)
        
        result = await middleware(handler, mock_tg_message, {})
        assert result is None
        handler.assert_not_called()


@pytest.mark.asyncio
async def test_whitelist_middleware_new_chats_disabled(mock_tg_message):
    middleware = WhitelistMiddleware()
    handler = AsyncMock(return_value="handled")
    
    with patch("src.bot.telegram.middleware.Setting.get_or_none", new_callable=AsyncMock) as mock_setting, \
         patch("src.bot.telegram.middleware.AllowedChat.get_or_none", new_callable=AsyncMock, return_value=None):
        
        async def mock_settings_get(*args, **kwargs):
            key = kwargs.get("key")
            if key == "telegram_bot_enabled":
                return MagicMock(value="True")
            elif key == "telegram_allow_new_chats":
                return MagicMock(value="False")
            else:
                return MagicMock(value="True")
            
        mock_setting.side_effect = mock_settings_get
        
        result = await middleware(handler, mock_tg_message, {})
        assert result is None
        handler.assert_not_called()


@pytest.mark.asyncio
async def test_whitelist_middleware_private_chat_disabled(mock_tg_message):
    middleware = WhitelistMiddleware()
    handler = AsyncMock(return_value="handled")
    mock_tg_message.chat.type = "private"
    
    with patch("src.bot.telegram.middleware.Setting.get_or_none", new_callable=AsyncMock) as mock_setting, \
         patch("src.bot.telegram.middleware.AllowedChat.get_or_none", new_callable=AsyncMock, return_value=None):
        
        async def mock_settings_get(*args, **kwargs):
            key = kwargs.get("key")
            if key == "telegram_bot_enabled":
                return MagicMock(value="True")
            elif key == "telegram_allow_new_chats":
                return MagicMock(value="True")
            elif key == "allow_private_chat":
                return MagicMock(value="False")
            
        mock_setting.side_effect = mock_settings_get
        
        result = await middleware(handler, mock_tg_message, {})
        assert result is None
        handler.assert_not_called()


@pytest.mark.asyncio
async def test_whitelist_middleware_private_chat_enabled(mock_tg_message):
    middleware = WhitelistMiddleware()
    handler = AsyncMock(return_value="handled")
    mock_tg_message.chat.type = "private"
    
    with patch("src.bot.telegram.middleware.Setting.get_or_none", new_callable=AsyncMock) as mock_setting, \
         patch("src.bot.telegram.middleware.AllowedChat.get_or_none", new_callable=AsyncMock, return_value=None):
        
        async def mock_settings_get(*args, **kwargs):
            return MagicMock(value="True")
            
        mock_setting.side_effect = mock_settings_get
        
        result = await middleware(handler, mock_tg_message, {})
        assert result == "handled"
        handler.assert_called_once()
