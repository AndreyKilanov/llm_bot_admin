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
    
    with patch("src.bot.discord.handlers.Setting.get_or_none", new_callable=AsyncMock) as mock_setting:
        mock_setting.return_value = MagicMock(value="False")
        
        await handler.handle_message(mock_discord_message)
        
        mock_discord_message.channel.typing.assert_not_called()

@pytest.mark.asyncio
async def test_handle_message_channel_disabled_in_whitelist(mock_bot_fake, mock_discord_message):
    handler = MessageHandler(mock_bot_fake)
    
    with patch("src.bot.discord.handlers.Setting.get_or_none", new_callable=AsyncMock) as mock_setting, \
         patch("src.bot.discord.handlers.AllowedChat.get_or_none", new_callable=AsyncMock) as mock_allowed:
        
        mock_setting.return_value = MagicMock(value="True")
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
    
    with patch("src.bot.discord.handlers.Setting.get_or_none", new_callable=AsyncMock) as mock_setting, \
         patch("src.bot.discord.handlers.AllowedChat.get_or_none", return_value=None, new_callable=AsyncMock), \
         patch("src.bot.discord.handlers.HistoryService.add_message", new_callable=AsyncMock) as mock_add_msg, \
         patch("src.bot.discord.handlers.HistoryService.get_last_messages", new_callable=AsyncMock) as mock_get_msg, \
         patch("src.bot.discord.handlers.LLMService.generate_response", new_callable=AsyncMock) as mock_llm_gen:
        
        async def mock_settings_get(*args, **kwargs):
            if kwargs.get('key') == "discord_memory_limit":
                return MagicMock(value="10")
            return MagicMock(value="True")
            
        mock_setting.side_effect = mock_settings_get
        mock_llm_gen.return_value = "Hello user!"
        
        await handler.handle_message(mock_discord_message)
        
        mock_add_msg.assert_called()
        mock_llm_gen.assert_called_once()
        mock_discord_message.channel.send.assert_called_once_with("Hello user!")
