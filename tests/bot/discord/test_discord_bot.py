import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.bot.discord import DiscordBot
from src.bot.discord.commands.playback import PlaybackCommands
from src.bot.discord.commands.control import ControlCommands
from src.schemas import TrackInfo

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
    with patch("src.bot.discord.client.settings") as mock_settings:
        mock_settings.DISCORD_BOT_TOKEN = "test_token"
        await mock_bot_instance.start()
        mock_bot_instance.bot.start.assert_called_once_with("test_token")

@pytest.mark.asyncio
async def test_discord_bot_stop(mock_bot_instance):
    mock_player = AsyncMock()
    mock_player.guild_id = 123
    with patch("src.bot.discord.client.PlayerFactory.get_all_players", return_value={123: mock_player}):
        await mock_bot_instance.stop()
        mock_player.disconnect.assert_called_once()
        mock_bot_instance.bot.close.assert_called_once()

@pytest.mark.asyncio
async def test_handle_playmusic(mock_bot_instance, mock_discord_ctx):
    with patch("src.services.SettingsService.is_discord_bot_enabled", new_callable=AsyncMock, return_value=True), \
         patch("src.services.SettingsService.is_discord_music_enabled", new_callable=AsyncMock, return_value=True), \
         patch("src.services.MusicService.search_tracks", new_callable=AsyncMock) as mock_search, \
         patch("src.bot.discord.commands.base.PlayerFactory.get_player") as mock_get_player, \
         patch("src.bot.discord.commands.base.BaseMusicCog.send_player_ui", new_callable=AsyncMock) as mock_send_ui:
        
        track = TrackInfo(title="Test Track", raw_title="Test Track", url="https://youtube.com/watch?v=123", duration=100, uploader="Test")
        mock_search.return_value = [track]
        
        mock_player = MagicMock()
        mock_player.connect = AsyncMock(return_value=True)
        mock_player.is_playing = False
        mock_player.current_track = track
        mock_player.add_to_queue = MagicMock()
        mock_player.play_from_start = AsyncMock()
        mock_player.set_text_channel = MagicMock()
        mock_player.get_playback_position.return_value = (0, 0)
        mock_player.get_queue_info.return_value = {"total": 1, "current_index": 0}
        
        mock_get_player.return_value = mock_player
        
        playback_cog = PlaybackCommands(mock_bot_instance.bot)
        
        # Заглушаем defer
        mock_discord_ctx.defer = AsyncMock()
        
        await playback_cog.play_music_cmd.callback(playback_cog, mock_discord_ctx, query="query")
        
        mock_search.assert_called_once()
        mock_player.connect.assert_called_once()
        mock_player.play_from_start.assert_called_once()

@pytest.mark.asyncio
async def test_handle_skip(mock_bot_instance, mock_discord_ctx):
    with patch("src.services.SettingsService.is_discord_bot_enabled", new_callable=AsyncMock, return_value=True), \
         patch("src.services.SettingsService.is_discord_music_enabled", new_callable=AsyncMock, return_value=True), \
         patch("src.bot.discord.commands.base.PlayerFactory.get_player") as mock_get_player:
        
        mock_player = MagicMock()
        mock_player.is_playing = True
        mock_player.play_next = AsyncMock(return_value=True)
        mock_get_player.return_value = mock_player
        
        control_cog = ControlCommands(mock_bot_instance.bot)
        
        await control_cog.skip_cmd.callback(control_cog, mock_discord_ctx)
        mock_player.play_next.assert_called_once()

@pytest.mark.asyncio
async def test_handle_stop(mock_bot_instance, mock_discord_ctx):
    with patch("src.services.SettingsService.is_discord_bot_enabled", new_callable=AsyncMock, return_value=True), \
         patch("src.services.SettingsService.is_discord_music_enabled", new_callable=AsyncMock, return_value=True), \
         patch("src.bot.discord.commands.base.PlayerFactory.get_player") as mock_get_player:
        
        mock_player = MagicMock()
        mock_player.is_playing = True
        mock_player.stop = AsyncMock()
        mock_player.disconnect = AsyncMock()
        mock_get_player.return_value = mock_player
        
        control_cog = ControlCommands(mock_bot_instance.bot)
        
        await control_cog.stop_cmd.callback(control_cog, mock_discord_ctx)
        mock_player.stop.assert_called_once()

@pytest.mark.asyncio
async def test_handle_playlist(mock_bot_instance, mock_discord_ctx):
    with patch("src.services.SettingsService.is_discord_bot_enabled", new_callable=AsyncMock, return_value=True), \
         patch("src.services.SettingsService.is_discord_music_enabled", new_callable=AsyncMock, return_value=True), \
         patch("src.services.MusicService.get_playlist_info", new_callable=AsyncMock) as mock_get_playlist, \
         patch("src.services.MusicService.is_valid_url", return_value=True), \
         patch("src.bot.discord.commands.base.PlayerFactory.get_player") as mock_get_player, \
         patch("src.bot.discord.commands.base.BaseMusicCog.send_player_ui", new_callable=AsyncMock) as mock_send_ui:
        
        t1 = TrackInfo(title="T1", raw_title="T1", url="https://youtube.com/watch?v=1", duration=100, uploader="A1")
        t2 = TrackInfo(title="T2", raw_title="T2", url="https://youtube.com/watch?v=2", duration=200, uploader="A2")
        mock_get_playlist.return_value = [t1, t2]
        
        mock_player = MagicMock()
        mock_player.connect = AsyncMock(return_value=True)
        mock_player.is_playing = False
        mock_player.current_track = t1
        mock_player.add_to_queue = MagicMock()
        mock_player.play_from_start = AsyncMock()
        mock_player.set_text_channel = MagicMock()
        mock_player.get_playback_position.return_value = (0, 0)
        mock_player.get_queue_info.return_value = {"total": 2, "current_index": 0}
        
        mock_get_player.return_value = mock_player
        
        playback_cog = PlaybackCommands(mock_bot_instance.bot)
        
        mock_discord_ctx.defer = AsyncMock()
        
        await playback_cog.play_playlist_cmd.callback(playback_cog, mock_discord_ctx, url="http://youtube.com/playlist?list=XXX")
        
        mock_get_playlist.assert_called_once()
        mock_player.connect.assert_called_once()
        mock_player.add_to_queue.assert_called_once()
        mock_player.play_from_start.assert_called_once()
