import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock, PropertyMock
from src.bot.discord.bot import DiscordBot

@pytest.fixture
def mock_bot_discord():
    # Instantiate actual bot to properly run decorators like @hybrid_command
    with patch("discord.opus.load_opus"):
        bot_instance = DiscordBot()
        bot_instance.bot.start = AsyncMock()
        bot_instance.bot.close = AsyncMock()
        bot_instance.bot.tree.sync = AsyncMock(return_value=["cmd1"])
        return bot_instance

@pytest.mark.asyncio
async def test_discord_bot_start(mock_bot_discord):
    with patch("src.bot.discord.bot.settings") as mock_settings:
        mock_settings.DISCORD_BOT_TOKEN = "test_token"
        
        # Test start
        await mock_bot_discord.start()
        mock_bot_discord.bot.start.assert_called_once_with("test_token")

@pytest.mark.asyncio
async def test_discord_bot_start_no_token(mock_bot_discord):
    with patch("src.bot.discord.bot.settings") as mock_settings:
        mock_settings.DISCORD_BOT_TOKEN = None
        
        await mock_bot_discord.start()
        mock_bot_discord.bot.start.assert_not_called()

@pytest.mark.asyncio
async def test_discord_bot_stop(mock_bot_discord):
    # Setup a dummy player in players dict
    mock_player = AsyncMock()
    mock_bot_discord.music_players[123] = mock_player
    
    await mock_bot_discord.stop()
    
    # Assert player disconnected
    mock_player.disconnect.assert_called_once()
    # Assert bot closed
    mock_bot_discord.bot.close.assert_called_once()

@pytest.mark.asyncio
async def test_on_message_no_text(mock_bot_discord):
    message = MagicMock()
    message.author.bot = False
    message.text = None
    message.content = ""
    message.guild = None # Private message
    
    with patch.object(type(mock_bot_discord.bot), 'user', new_callable=PropertyMock) as mock_user:
        mock_user.return_value = MagicMock()
        mock_user.return_value.id = 12345
        await mock_bot_discord.on_message(message)
    # Just verify no crash

@pytest.mark.asyncio
async def test_on_ready(mock_bot_discord):
    mock_bot_discord.bot.tree.sync = AsyncMock(return_value=["cmd1", "cmd2"])
    await mock_bot_discord.on_ready()
    mock_bot_discord.bot.tree.sync.assert_awaited_once()

@pytest.mark.asyncio
async def test_get_or_create_player(mock_bot_discord):
    # Initially empty
    assert 123 not in mock_bot_discord.music_players
    
    player1 = mock_bot_discord._get_or_create_player(123)
    assert 123 in mock_bot_discord.music_players
    
    player2 = mock_bot_discord._get_or_create_player(123)
    assert player1 is player2

@pytest.mark.asyncio
@patch("src.bot.discord.bot.SettingsService.is_discord_music_enabled", return_value=True)
@patch("src.bot.discord.bot.music_service.search_tracks")
async def test_handle_playmusic_single_track(mock_search, mock_settings_srv, mock_bot_discord, mock_discord_ctx):
    # Setup search result
    mock_search.return_value = [{"title": "Test Track", "url": "test", "duration": 100, "uploader": "Test"}]
    
    # Needs a real or mock player
    with patch.object(mock_bot_discord, '_get_or_create_player') as mock_get_player:
        mock_player = AsyncMock()
        mock_player.connect.return_value = True
        mock_player.is_playing = False
        mock_player.add_to_queue = MagicMock()
        mock_player.set_text_channel = MagicMock()
        mock_get_player.return_value = mock_player
        
        with patch.object(mock_bot_discord, '_send_player_ui') as mock_send_ui:
            await mock_bot_discord._handle_playmusic(mock_discord_ctx, "query")
            
            # Assert search
            mock_search.assert_called_once_with("query", max_results=5)
            # Assert player connect
            mock_player.connect.assert_called_once()
            # Assert player play from start
            mock_player.play_from_start.assert_called_once()
            # Assert UI sent
            mock_send_ui.assert_called_once()

@pytest.mark.asyncio
@patch("src.bot.discord.bot.SettingsService.is_discord_music_enabled", return_value=True)
async def test_handle_playmusic_no_voice(mock_settings_srv, mock_bot_discord, mock_discord_ctx):
    mock_discord_ctx.author.voice = None
    await mock_bot_discord._handle_playmusic(mock_discord_ctx, "query")
    mock_discord_ctx.send.assert_called_with("❌ Вы должны находиться в голосовом канале!")

@pytest.mark.asyncio
@patch("src.bot.discord.bot.SettingsService.is_discord_music_enabled", return_value=False)
async def test_handle_command_disabled(mock_settings_srv, mock_bot_discord, mock_discord_ctx):
    await mock_bot_discord._handle_playmusic(mock_discord_ctx, "query")
    mock_discord_ctx.send.assert_called_with("❌ Музыкальный плеер отключен в настройках администратора.")
    
@pytest.mark.asyncio
@patch("src.bot.discord.bot.SettingsService.is_discord_music_enabled", return_value=True)
@patch("src.bot.discord.bot.music_service.is_valid_url", return_value=True)
@patch("src.bot.discord.bot.music_service.get_track_info")
async def test_handle_link(mock_get_info, mock_is_valid, mock_settings_srv, mock_bot_discord, mock_discord_ctx):
    mock_get_info.return_value = {"title": "Test Track", "url": "test", "duration": 100, "uploader": "Test"}
    
    with patch.object(mock_bot_discord, '_get_or_create_player') as mock_get_player:
        mock_player = AsyncMock()
        mock_player.connect.return_value = True
        mock_player.is_playing = False
        mock_player.add_to_queue = MagicMock()
        mock_player.set_text_channel = MagicMock()
        mock_get_player.return_value = mock_player
        
        with patch.object(mock_bot_discord, '_send_player_ui'):
            await mock_bot_discord._handle_link(mock_discord_ctx, "https://youtube.com/watch?v=123")
            mock_get_info.assert_called_once()
            mock_player.add_to_queue.assert_called_once()

@pytest.mark.asyncio
@patch("src.bot.discord.bot.SettingsService.is_discord_music_enabled", return_value=True)
async def test_handle_skip(mock_settings_srv, mock_bot_discord, mock_discord_ctx):
    # No player
    await mock_bot_discord._handle_skip(mock_discord_ctx)
    mock_discord_ctx.send.assert_called_with("❌ Ничего не воспроизводится.")
    
    # With player
    mock_player = AsyncMock()
    mock_player.is_playing = True
    mock_player.play_next.return_value = True
    mock_bot_discord.music_players[123] = mock_player
    
    await mock_bot_discord._handle_skip(mock_discord_ctx)
    mock_player.play_next.assert_called_once()
    mock_discord_ctx.send.assert_called_with("⏭️ Переключено на следующий трек.")
    
@pytest.mark.asyncio
@patch("src.bot.discord.bot.SettingsService.is_discord_music_enabled", return_value=True)
async def test_handle_stop(mock_settings_srv, mock_bot_discord, mock_discord_ctx):
    mock_player = AsyncMock()
    mock_bot_discord.music_players[123] = mock_player
    
    await mock_bot_discord._handle_stop(mock_discord_ctx)
    
    mock_player.stop.assert_called_once()
    mock_player.disconnect.assert_called_once()
    assert 123 not in mock_bot_discord.music_players
    mock_discord_ctx.send.assert_called_with("⏹️ Воспроизведение остановлено, бот отключен от канала.")

@pytest.mark.asyncio
@patch("src.bot.discord.bot.SettingsService.is_discord_music_enabled", return_value=True)
async def test_handle_help(mock_settings_srv, mock_bot_discord, mock_discord_ctx):
    await mock_bot_discord._handle_help(mock_discord_ctx)
    mock_discord_ctx.send.assert_called_once()
