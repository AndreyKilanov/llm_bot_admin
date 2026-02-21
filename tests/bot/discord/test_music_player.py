import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.bot.discord.music_player import LoopMode

@pytest.mark.asyncio
async def test_add_to_queue(discord_player):
    track1 = {"title": "Track 1", "url": "url1"}
    track2 = {"title": "Track 2", "url": "url2"}
    
    discord_player.add_to_queue([track1, track2])
    
    assert len(discord_player.queue) == 2
    assert discord_player.queue[0] == track1
    assert discord_player.queue[1] == track2

def test_get_queue_info_empty(discord_player):
    info = discord_player.get_queue_info()
    assert info["total"] == 0
    assert info["current_index"] == -1
    assert info["tracks"] == []

def test_get_queue_info(discord_player):
    track1 = {"title": "Track 1", "url": "url1"}
    discord_player.add_to_queue([track1])
    discord_player.current_index = 0
    
    info = discord_player.get_queue_info()
    assert info["total"] == 1
    assert info["current_index"] == 0
    assert len(info["tracks"]) == 1

@pytest.mark.asyncio
async def test_connect(discord_player, mock_voice_channel):
    # Using the mock_bot_fake from fixtures which has mock_guild
    from tests.fixtures import FakeVoiceClient
    vc = FakeVoiceClient(123)
    mock_voice_channel.fake_vc = vc
    
    # Success
    result = await discord_player.connect(mock_voice_channel)
    assert result is True
    assert discord_player._voice_channel == mock_voice_channel

@pytest.mark.asyncio
async def test_disconnect(discord_player):
    from tests.fixtures import FakeVoiceClient
    vc = FakeVoiceClient(123)
    discord_player.bot.voice_clients = [vc]
    discord_player.bot.mock_guild.voice_client = vc
    
    await discord_player.disconnect()
    assert vc.disconnect_called == 1
    assert discord_player._voice_channel is None
    assert discord_player.is_playing is False

@pytest.mark.asyncio
async def test_pause_resume(discord_player):
    from tests.fixtures import FakeVoiceClient
    vc = FakeVoiceClient(123)
    vc.is_playing_status = True
    discord_player.bot.voice_clients = [vc]
    discord_player.bot.mock_guild.voice_client = vc
    
    discord_player.is_playing = True
    discord_player.is_paused = False
    
    # Pause
    result = discord_player.pause()
    assert result is True
    assert discord_player.is_paused is True
    assert vc.pause_called == 1
    
    # Resume
    discord_player.is_paused = True
    vc.is_paused_status = True
    result2 = discord_player.resume()
    assert result2 is True
    assert discord_player.is_paused is False
    assert vc.resume_called == 1

@pytest.mark.asyncio
async def test_stop(discord_player):
    from tests.fixtures import FakeVoiceClient
    vc = FakeVoiceClient(123)
    vc.is_playing_status = True
    discord_player.bot.voice_clients = [vc]
    discord_player.bot.mock_guild.voice_client = vc
    discord_player.is_playing = True
    
    await discord_player.stop()
    assert discord_player.is_playing is False
    assert vc.stop_called == 1

def test_cycle_loop_mode(discord_player):
    assert discord_player.loop_mode == LoopMode.NONE
    
    assert discord_player.cycle_loop_mode() == LoopMode.TRACK
    assert discord_player.loop_mode == LoopMode.TRACK
    
    assert discord_player.cycle_loop_mode() == LoopMode.PLAYLIST
    assert discord_player.loop_mode == LoopMode.PLAYLIST
    
    assert discord_player.cycle_loop_mode() == LoopMode.NONE
    assert discord_player.loop_mode == LoopMode.NONE

@pytest.mark.asyncio
async def test_loop_mode_logic(discord_player, mock_voice_channel):
    from tests.fixtures import FakeVoiceClient
    vc = FakeVoiceClient(123)
    discord_player.bot.mock_guild.voice_client = vc
    await discord_player.connect(mock_voice_channel)
    
    tracks = [{"title": f"T{i}", "url": f"u{i}", "duration": 100, "uploader": "U"} for i in range(3)]
    discord_player.add_to_queue(tracks)
    
    with patch("src.bot.discord.music_player.music_service.get_audio_source", new_callable=AsyncMock) as mock_get_source:
        mock_get_source.return_value = MagicMock()
        await discord_player.play_from_start()
        assert discord_player.current_index == 0
        
        # Loop TRACK
        discord_player.loop_mode = LoopMode.TRACK
        await discord_player.play_next()
        assert discord_player.current_index == 0
        
        # Loop NONE
        discord_player.loop_mode = LoopMode.NONE
        await discord_player.play_next()
        assert discord_player.current_index == 1
        
        # Loop PLAYLIST
        discord_player.current_index = 2
        discord_player.loop_mode = LoopMode.PLAYLIST
        await discord_player.play_next()
        assert discord_player.current_index == 0

@pytest.mark.asyncio
async def test_seek_relative(discord_player, mock_voice_channel):
    from tests.fixtures import FakeVoiceClient
    vc = FakeVoiceClient(123)
    discord_player.bot.mock_guild.voice_client = vc
    await discord_player.connect(mock_voice_channel)
    
    track = {"title": "T", "url": "u", "duration": 100, "uploader": "U"}
    discord_player.add_to_queue([track])
    
    with patch("src.bot.discord.music_player.music_service.get_audio_source", new_callable=AsyncMock) as mock_get_source:
        mock_get_source.return_value = MagicMock()
        await discord_player.play_from_start()
        
        discord_player.start_time = 1000
        with patch("time.time", return_value=1050):
            result = await discord_player.seek_relative(10)
            assert result is True
            mock_get_source.assert_called_with("u", start_time=60)
