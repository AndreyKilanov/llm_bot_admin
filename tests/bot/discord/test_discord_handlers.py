import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.bot.discord.handlers import MessageHandler

@pytest.mark.asyncio
async def test_handle_message_from_bot_itself(mock_bot_fake, mock_discord_message):
    handler = MessageHandler(mock_bot_fake)
    mock_discord_message.author = mock_bot_fake.user = MagicMock()
    mock_discord_message.author.id = 999
    mock_bot_fake.user.id = 999
    
    await handler.handle_message(mock_discord_message)
    mock_discord_message.channel.typing.assert_not_called()

@pytest.mark.asyncio
async def test_handle_message_slash_command(mock_bot_fake, mock_discord_message):
    handler = MessageHandler(mock_bot_fake)
    mock_discord_message.content = "/playmusic track"
    
    await handler.handle_message(mock_discord_message)
    mock_discord_message.channel.typing.assert_not_called()

@pytest.mark.asyncio
async def test_handle_message_bot_disabled(mock_bot_fake, mock_discord_message):
    handler = MessageHandler(mock_bot_fake)
    
    with patch("src.bot.discord.handlers.SettingsService.is_discord_bot_enabled", new_callable=AsyncMock) as mock_setting:
        mock_setting.return_value = False
        
        await handler.handle_message(mock_discord_message)
        
        mock_discord_message.channel.typing.assert_not_called()

@pytest.mark.asyncio
async def test_handle_message_channel_disabled_in_whitelist(mock_bot_fake, mock_discord_message):
    handler = MessageHandler(mock_bot_fake)
    
    with patch("src.bot.discord.handlers.SettingsService.is_discord_bot_enabled", return_value=True, new_callable=AsyncMock), \
         patch("src.bot.discord.handlers.AllowedChat.get_or_none", new_callable=AsyncMock) as mock_allowed:
        
        mock_allowed.return_value = MagicMock(is_active=False)
        
        await handler.handle_message(mock_discord_message)
        
        mock_discord_message.channel.typing.assert_not_called()

@pytest.mark.asyncio
async def test_handle_message_success(mock_bot_fake, mock_discord_message):
    mock_bot_fake.user = MagicMock(id=999)
    mock_bot_fake.user.name = "TestBot"
    handler = MessageHandler(mock_bot_fake)
    mock_discord_message.mentions = [mock_bot_fake.user]
    mock_discord_message.clean_content = "@TestBot hello"
    
    async def mock_settings_get(*args, **kwargs):
        key = kwargs.get('key')
        if key == "discord_memory_limit":
            return MagicMock(value="10")
        if key == "discord_allow_new_chats":
            return MagicMock(value="True")
        return MagicMock(value="True")

    with patch("src.bot.discord.handlers.SettingsService.is_discord_bot_enabled", return_value=True, new_callable=AsyncMock), \
         patch("src.bot.discord.handlers.SettingsService.should_respond_to_everyone", return_value=False, new_callable=AsyncMock), \
         patch("src.bot.discord.handlers.Setting.get_or_none", side_effect=mock_settings_get, new_callable=AsyncMock), \
         patch("src.bot.discord.handlers.AllowedChat.get_or_none", return_value=None, new_callable=AsyncMock), \
         patch("src.bot.discord.handlers.HistoryService.add_message", new_callable=AsyncMock) as mock_add_msg, \
         patch("src.bot.discord.handlers.HistoryService.get_last_messages", new_callable=AsyncMock) as mock_get_msg, \
         patch("src.bot.discord.handlers.LLMService.generate_response", new_callable=AsyncMock) as mock_llm_gen:
        
        mock_llm_gen.return_value = "Hello user!"
        
        await handler.handle_message(mock_discord_message)
        
        mock_add_msg.assert_called()
        mock_llm_gen.assert_called_once()
        mock_discord_message.channel.send.assert_called_once_with("Hello user!")

@pytest.mark.asyncio
async def test_handle_message_no_mention_default(mock_bot_fake, mock_discord_message):
    """Проверка, что бот НЕ отвечает без упоминания по умолчанию."""
    mock_bot_fake.user = MagicMock(id=999)
    handler = MessageHandler(mock_bot_fake)
    mock_discord_message.mentions = []
    mock_discord_message.clean_content = "hello bot"
    
    with patch("src.bot.discord.handlers.SettingsService.is_discord_bot_enabled", return_value=True, new_callable=AsyncMock), \
         patch("src.bot.discord.handlers.SettingsService.should_respond_to_everyone", return_value=False, new_callable=AsyncMock), \
         patch("src.bot.discord.handlers.AllowedChat.get_or_none", return_value=MagicMock(is_active=True), new_callable=AsyncMock):
        
        await handler.handle_message(mock_discord_message)
        
        mock_discord_message.channel.typing.assert_not_called()

@pytest.mark.asyncio
async def test_handle_message_no_mention_respond_everyone(mock_bot_fake, mock_discord_message):
    """Проверка, что бот ОТВЕЧАЕТ без упоминания, если включена настройка 'отвечать всем'."""
    mock_bot_fake.user = MagicMock(id=999)
    handler = MessageHandler(mock_bot_fake)
    mock_discord_message.mentions = []
    mock_discord_message.clean_content = "hello bot"
    
    with patch("src.bot.discord.handlers.SettingsService.is_discord_bot_enabled", return_value=True, new_callable=AsyncMock), \
         patch("src.bot.discord.handlers.SettingsService.should_respond_to_everyone", return_value=True, new_callable=AsyncMock), \
         patch("src.bot.discord.handlers.AllowedChat.get_or_none", return_value=MagicMock(is_active=True), new_callable=AsyncMock), \
         patch("src.bot.discord.handlers.Setting.get_or_none", return_value=MagicMock(value="10"), new_callable=AsyncMock), \
         patch("src.bot.discord.handlers.HistoryService.add_message", new_callable=AsyncMock), \
         patch("src.bot.discord.handlers.HistoryService.get_last_messages", new_callable=AsyncMock), \
         patch("src.bot.discord.handlers.LLMService.generate_response", return_value="Resp", new_callable=AsyncMock):
        
        await handler.handle_message(mock_discord_message)
        
        mock_discord_message.channel.send.assert_called_once_with("Resp")
