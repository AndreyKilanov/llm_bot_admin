import sys
import os
sys.path.append(os.getcwd())
from unittest.mock import AsyncMock, MagicMock, patch

# Mock discord module before importing anything that uses it
sys.modules["discord"] = MagicMock()
sys.modules["discord.ext"] = MagicMock()
sys.modules["discord.ext.commands"] = MagicMock()
sys.modules["discord.ui"] = MagicMock()
sys.modules["yt_dlp"] = MagicMock()

import pytest
from src.bot.discord.music_player import MusicPlayer, LoopMode


class TestMusicPlayer:
    """Тесты для класса MusicPlayer."""
    
    @pytest.fixture
    def player(self):
        """Фикстура для создания экземпляра плеера."""
        bot = MagicMock()
        return MusicPlayer(guild_id=123456789, bot=bot)
    
    @pytest.fixture
    def mock_voice_channel(self):
        """Фикстура для мок голосового канала."""
        channel = MagicMock()
        channel.id = 987654321
        channel.name = "Test Voice Channel"
        return channel
    
    @pytest.fixture
    def sample_tracks(self):
        """Фикстура с примерами треков."""
        return [
            {
                "title": "Track 1",
                "url": "https://youtube.com/watch?v=test1",
                "duration": 180,
                "thumbnail": "https://example.com/thumb1.jpg",
                "uploader": "Channel 1",
                "id": "test1",
            },
            {
                "title": "Track 2",
                "url": "https://youtube.com/watch?v=test2",
                "duration": 240,
                "thumbnail": "https://example.com/thumb2.jpg",
                "uploader": "Channel 2",
                "id": "test2",
            },
            {
                "title": "Track 3",
                "url": "https://youtube.com/watch?v=test3",
                "duration": 200,
                "thumbnail": "https://example.com/thumb3.jpg",
                "uploader": "Channel 3",
                "id": "test3",
            }
        ]
    
    def test_initialization(self, player):
        """Тест инициализации плеера."""
        player.bot.get_guild.return_value = None
        assert player.guild_id == 123456789
        assert player.voice_client is None
        assert player.queue == []
        assert player.current_track is None
        assert player.current_index == -1
        assert player.is_playing is False
        assert player.is_paused is False
    
    def test_add_to_queue(self, player, sample_tracks):
        """Тест добавления треков в очередь."""
        player.add_to_queue(sample_tracks[:2])
        assert len(player.queue) == 2
        assert player.queue[0]["title"] == "Track 1"
        
        player.add_to_queue([sample_tracks[2]])
        assert len(player.queue) == 3
        assert player.queue[2]["title"] == "Track 3"
    
    def test_get_queue_info_empty(self, player):
        """Тест получения информации о пустой очереди."""
        queue_info = player.get_queue_info()
        
        assert queue_info["total"] == 0
        assert queue_info["current_index"] == -1
        assert queue_info["current_track"] is None
        assert queue_info["tracks"] == []
        assert queue_info["is_playing"] is False
        assert queue_info["is_paused"] is False
    
    def test_get_queue_info_with_tracks(self, player, sample_tracks):
        """Тест получения информации об очереди с треками."""
        player.add_to_queue(sample_tracks)
        player.current_index = 1
        player.current_track = sample_tracks[1]
        player.is_playing = True
        
        queue_info = player.get_queue_info()
        
        assert queue_info["total"] == 3
        assert queue_info["current_index"] == 1
        assert queue_info["current_track"]["title"] == "Track 2"
        assert len(queue_info["tracks"]) == 3
        assert queue_info["is_playing"] is True
    
    @pytest.mark.asyncio
    async def test_stop(self, player, sample_tracks):
        """Тест остановки воспроизведения."""
        player.add_to_queue(sample_tracks)
        player.current_index = 1
        player.current_track = sample_tracks[1]
        player.is_playing = True
        
        # Мокируем voice_client через bot
        guild = MagicMock()
        voice_client = MagicMock()
        voice_client.is_playing.return_value = True
        guild.voice_client = voice_client
        player.bot.get_guild.return_value = guild
        
        await player.stop()
        
        assert len(player.queue) == 0
        assert player.current_track is None
        assert player.current_index == -1
        assert player.is_playing is False
        assert player.is_paused is False
    @pytest.mark.asyncio
    async def test_stop_playback(self, player, sample_tracks):
        """Тест остановки воспроизведения БЕЗ очистки очереди."""
        player.add_to_queue(sample_tracks)
        player.current_index = 1
        player.current_track = sample_tracks[1]
        player.is_playing = True
        
        # Мокируем voice_client через bot
        guild = MagicMock()
        voice_client = MagicMock()
        voice_client.is_playing.return_value = True
        guild.voice_client = voice_client
        player.bot.get_guild.return_value = guild
        
        await player.stop_playback()
        
        # Очередь должна остаться
        assert len(player.queue) == 3
        assert player.current_track is None
        assert player.current_index == -1
        assert player.is_playing is False
        player.voice_client.stop.assert_called_once()

    
    @pytest.mark.asyncio
    async def test_pause(self, player):
        """Тест паузы воспроизведения."""
        # Мокируем voice_client через bot
        guild = MagicMock()
        voice_client = MagicMock()
        voice_client.is_playing.return_value = True
        guild.voice_client = voice_client
        player.bot.get_guild.return_value = guild
        
        result = player.pause()
        
        assert result is True
        assert player.is_paused is True
        player.voice_client.pause.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_pause_not_playing(self, player):
        """Тест паузы когда ничего не воспроизводится."""
        result = player.pause()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_resume(self, player):
        """Тест возобновления воспроизведения."""
        # Мокируем voice_client через bot
        guild = MagicMock()
        voice_client = MagicMock()
        voice_client.is_paused.return_value = True
        guild.voice_client = voice_client
        player.bot.get_guild.return_value = guild
        player.is_paused = True
        
        result = player.resume()
        
        assert result is True
        assert player.is_paused is False
        player.voice_client.resume.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_resume_not_paused(self, player):
        """Тест возобновления когда воспроизведение не на паузе."""
        result = player.resume()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_disconnect(self, player, sample_tracks):
        """Тест отключения от голосового канала."""
        player.add_to_queue(sample_tracks)
        
        # Мокируем voice_client через bot
        guild = MagicMock()
        voice_client = AsyncMock()
        # Для is_connected
        voice_client.is_connected.return_value = True
        guild.voice_client = voice_client
        player.bot.get_guild.return_value = guild
        
        await player.disconnect()
        
        player.voice_client.disconnect.assert_called_once()
        assert player.voice_client is None
        assert len(player.queue) == 0
        assert player.current_index == -1
        assert player.current_track is None
