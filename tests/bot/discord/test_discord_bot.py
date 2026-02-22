import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.bot.discord.bot import DiscordBot
from src.bot.discord.bot.commands import CommandHandlers
from src.bot.discord.player import PlayerFactory

@pytest.fixture
def mock_bot_instance():
    with patch("discord.opus.load_opus"):
        bot_wrapper = DiscordBot()
        bot_wrapper.bot.start = AsyncMock()
        bot_wrapper.bot.close = AsyncMock()
        bot_wrapper.bot.tree.sync = AsyncMock(return_value=[])
        return bot_wrapper

@pytest.mark.asyncio
async def test_discord_bot_start(mock_bot_instance):
    with patch("src.bot.discord.bot.client.settings") as mock_settings:
        mock_settings.DISCORD_BOT_TOKEN = "test_token"
        await mock_bot_instance.start()
        mock_bot_instance.bot.start.assert_called_once_with("test_token")

@pytest.mark.asyncio
async def test_discord_bot_stop(mock_bot_instance):
    mock_player = AsyncMock()
    mock_player.guild_id = 123
    with patch("src.bot.discord.player.PlayerFactory.get_all_players", return_value={123: mock_player}):
        await mock_bot_instance.stop()
        mock_player.disconnect.assert_called_once()
        mock_bot_instance.bot.close.assert_called_once()

@pytest.mark.asyncio
async def test_handle_playmusic(mock_bot_instance, mock_discord_ctx):
    with patch("src.services.SettingsService.is_discord_bot_enabled", new_callable=AsyncMock, return_value=True), \
         patch("src.services.SettingsService.is_discord_music_enabled", new_callable=AsyncMock, return_value=True), \
         patch("src.bot.discord.bot.commands.music_service.search_tracks", new_callable=AsyncMock) as mock_search, \
         patch.object(CommandHandlers, "get_player") as mock_get_player:
        
        mock_search.return_value = [{"title": "Test Track", "url": "test", "duration": 100, "uploader": "Test"}]
        
        # Используем MagicMock для плеера, чтобы не-async методы работали правильно
        mock_player = MagicMock()
        mock_player.connect = AsyncMock(return_value=True)
        mock_player.is_playing = False
        mock_player.current_track = {
            "title": "Test Track", 
            "url": "http://test", 
            "uploader": "Test Uploader",
            "duration": 100
        }
        mock_player.add_to_queue = MagicMock()
        mock_player.play_from_start = AsyncMock()
        mock_player.set_text_channel = MagicMock()
        
        mock_player.get_playback_position.return_value = (0, 0)
        mock_player.get_queue_info.return_value = {"total": 1, "current_index": 0}
        
        mock_get_player.return_value = mock_player
        
        await CommandHandlers.handle_playmusic(mock_bot_instance.bot, mock_discord_ctx, "query")
        
        mock_search.assert_called_once()
        mock_player.connect.assert_called_once()
        mock_player.play_from_start.assert_called_once()

@pytest.mark.asyncio
async def test_handle_skip(mock_bot_instance, mock_discord_ctx):
    with patch("src.services.SettingsService.is_discord_bot_enabled", new_callable=AsyncMock, return_value=True), \
         patch("src.services.SettingsService.is_discord_music_enabled", new_callable=AsyncMock, return_value=True), \
         patch.object(CommandHandlers, "get_player") as mock_get_player:
        
        mock_player = MagicMock()
        mock_player.is_playing = True
        mock_player.play_next = AsyncMock(return_value=True)
        mock_get_player.return_value = mock_player
        
        await CommandHandlers.handle_skip(mock_bot_instance.bot, mock_discord_ctx)
        mock_player.play_next.assert_called_once()

@pytest.mark.asyncio
async def test_handle_stop(mock_bot_instance, mock_discord_ctx):
    with patch("src.services.SettingsService.is_discord_bot_enabled", new_callable=AsyncMock, return_value=True), \
         patch("src.services.SettingsService.is_discord_music_enabled", new_callable=AsyncMock, return_value=True), \
         patch.object(CommandHandlers, "get_player") as mock_get_player:
        
        mock_player = MagicMock()
        mock_player.stop = AsyncMock()
        mock_player.disconnect = AsyncMock()
        mock_get_player.return_value = mock_player
        
        await CommandHandlers.handle_stop(mock_bot_instance.bot, mock_discord_ctx)
        mock_player.stop.assert_called_once()
        mock_player.disconnect.assert_called_once()
