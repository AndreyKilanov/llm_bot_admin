import pytest
import discord
from unittest.mock import AsyncMock, patch, MagicMock

from src.bot.discord.views import TrackSelectionView, MusicPlayerView
from src.bot.discord.music_player import LoopMode


@pytest.fixture
def mock_ctx():
    ctx = AsyncMock()
    ctx.author = MagicMock()
    ctx.author.voice = MagicMock()
    ctx.author.voice.channel = MagicMock()
    return ctx


@pytest.fixture
def mock_player():
    player = AsyncMock()
    player.current_track = {
        "title": "Test song",
        "uploader": "Artist",
        "duration": 180,
        "url": "http://example.com/test",
        "thumbnail": None
    }
    player.queue = [player.current_track]
    player.is_playing = True
    player.is_paused = False
    player.loop_mode = LoopMode.NONE
    player.get_queue_info.return_value = {
        "total": 1,
        "current_index": 0,
        "tracks": player.queue
    }
    player.get_playback_position = MagicMock(return_value=(60, 180))
    player.get_queue_info = MagicMock(return_value={
        "total": 1,
        "current_index": 0,
        "tracks": player.queue
    })
    player.pause = MagicMock(return_value=True)
    player.resume = MagicMock(return_value=True)
    player.cycle_loop_mode = MagicMock(return_value=LoopMode.TRACK)
    player.add_to_queue = MagicMock()
    player.set_text_channel = MagicMock()
    player.connect.return_value = True
    return player


@pytest.fixture
def mock_interaction():
    interaction = AsyncMock()
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    return interaction


@pytest.mark.asyncio
async def test_track_selection_view(mock_ctx, mock_player, mock_interaction):
    tracks = [{"title": f"Song {i}", "url": f"http://song{i}"} for i in range(5)]
    view = TrackSelectionView(tracks, mock_player, mock_ctx)
    
    # Simulate first track selection
    callback = view._create_callback(0)
    await callback(mock_interaction)
    
    mock_interaction.response.defer.assert_called_once()
    mock_player.connect.assert_called_once_with(mock_ctx.author.voice.channel)
    mock_player.add_to_queue.assert_called_once_with([tracks[0]])
    mock_interaction.edit_original_response.assert_called_once()


@pytest.mark.asyncio
async def test_track_selection_view_add_all(mock_ctx, mock_player, mock_interaction):
    tracks = [{"title": f"Song {i}", "url": f"http://song{i}"} for i in range(5)]
    view = TrackSelectionView(tracks, mock_player, mock_ctx)
    
    await view._add_all_callback(mock_interaction)
    
    mock_interaction.response.defer.assert_called_once()
    mock_player.connect.assert_called_once_with(mock_ctx.author.voice.channel)
    mock_player.add_to_queue.assert_called_once_with(tracks)
    mock_interaction.edit_original_response.assert_called_once()


@pytest.mark.asyncio
async def test_track_selection_view_no_voice(mock_ctx, mock_player, mock_interaction):
    tracks = [{"title": "Song", "url": "http://song"}]
    mock_ctx.author.voice = None
    view = TrackSelectionView(tracks, mock_player, mock_ctx)
    
    callback = view._create_callback(0)
    await callback(mock_interaction)
    
    mock_interaction.response.send_message.assert_called_once_with("❌ Вы больше не в голосовом канале!", ephemeral=True)


@pytest.mark.asyncio
async def test_music_player_view_buttons(mock_ctx, mock_player, mock_interaction):
    view = MusicPlayerView(mock_player, mock_ctx)
    view.message = AsyncMock()
    view.message.guild = None
    
    # Previous button
    mock_player.play_previous.return_value = True
    await view.previous_button.callback(mock_interaction)
    mock_player.play_previous.assert_called_once()
    
    # Next button
    mock_player.play_next.return_value = True
    await view.next_button.callback(mock_interaction)
    mock_player.play_next.assert_called_once()
    
    # Pause/Resume button
    mock_player.is_paused = False
    mock_player.pause.return_value = True
    await view.pause_resume_button.callback(mock_interaction)
    mock_player.pause.assert_called_once()
    
    # Stop button
    await view.stop_button.callback(mock_interaction)
    mock_player.stop.assert_called_once()


@pytest.mark.asyncio
async def test_music_player_rewind_forward(mock_ctx, mock_player, mock_interaction):
    view = MusicPlayerView(mock_player, mock_ctx)
    view.message = AsyncMock()
    view.message.guild = None
    
    with patch("src.bot.discord.views.SettingsService.get_discord_seek_time", new_callable=AsyncMock) as mock_seek:
        mock_seek.return_value = 10
        mock_player.seek_relative.return_value = True
        
        await view.rewind_button.callback(mock_interaction)
        mock_player.seek_relative.assert_called_with(-10)
        
        await view.forward_button.callback(mock_interaction)
        mock_player.seek_relative.assert_called_with(10)


@pytest.mark.asyncio
async def test_music_player_queue_button(mock_ctx, mock_player, mock_interaction):
    view = MusicPlayerView(mock_player, mock_ctx)
    view.message = AsyncMock()
    view.message.guild = None
    
    await view.queue_button.callback(mock_interaction)
    mock_interaction.followup.send.assert_called_once()
    args, kwargs = mock_interaction.followup.send.call_args
    assert "embed" in kwargs


@pytest.mark.asyncio
async def test_music_player_loop_mode(mock_ctx, mock_player, mock_interaction):
    view = MusicPlayerView(mock_player, mock_ctx)
    view.message = AsyncMock()
    view.message.guild = None
    
    mock_player.cycle_loop_mode.return_value = LoopMode.TRACK
    
    await view.loop_mode_button.callback(mock_interaction)
    mock_player.cycle_loop_mode.assert_called_once()
    mock_interaction.followup.send.assert_called_once()
    args, kwargs = mock_interaction.followup.send.call_args
    assert "трека" in args[0]
