"""
Тесты для музыкального сервиса.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.music_service import MusicService, music_service


class TestMusicService:
    """Тесты для класса MusicService."""
    
    @pytest.fixture
    def service(self):
        """Фикстура для создания экземпляра сервиса."""
        srv = MusicService()
        srv._search_cache.clear()
        srv._info_cache.clear()
        return srv
    
    def test_singleton(self, service):
        """Тест паттерна Singleton."""
        another_service = MusicService()
        assert service is another_service
        assert service is music_service
    
    def test_is_valid_url(self, service):
        """Тест валидации URL."""
        assert service.is_valid_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is True
        assert service.is_valid_url("https://youtu.be/dQw4w9WgXcQ") is True
        assert service.is_valid_url("https://m.youtube.com/watch?v=dQw4w9WgXcQ") is True
        assert service.is_valid_url("https://youtube.com/playlist?list=PL") is True
        assert service.is_valid_url("https://example.com/video") is False
        assert service.is_valid_url("not a url") is False

    @pytest.mark.asyncio
    async def test_search_tracks_success(self, service):
        """Тест успешного поиска треков."""
        mock_data = {
            "entries": [
                {
                    "title": "Test Track 1",
                    "webpage_url": "https://youtube.com/watch?v=test1",
                    "duration": 180,
                    "thumbnail": "https://example.com/thumb1.jpg",
                    "uploader": "Test Channel 1",
                    "id": "test1",
                },
                {
                    "title": "Test Track 2",
                    "webpage_url": "https://youtube.com/watch?v=test2",
                    "duration": 240,
                    "thumbnail": "https://example.com/thumb2.jpg",
                    "uploader": "Test Channel 2",
                    "id": "test2",
                }
            ]
        }
        
        with patch("yt_dlp.YoutubeDL") as mock_ytdl:
            mock_inst = mock_ytdl.return_value
            mock_inst.extract_info.return_value = mock_data
            mock_inst.__enter__.return_value = mock_inst
            
            tracks = await service.search_tracks("test query", max_results=2)
            
            assert len(tracks) == 2
            assert tracks[0].title == "Test Track 1"
            assert tracks[0].duration == 180
            assert tracks[1].title == "Test Track 2"
            
    @pytest.mark.asyncio
    async def test_search_tracks_cache(self, service):
        """Тест использования кэша при поиске."""
        from src.schemas import TrackInfo
        cached_track = TrackInfo(
            title="Cached Track",
            raw_title="Cached Track",
            url="https://youtube.com/watch?v=cached",
            duration=180,
            thumbnail="https://example.com/thumb.jpg",
            uploader="Test Uploader",
            id="cached"
        )
        service._search_cache["cached query:5:False"] = [cached_track]
        
        with patch("yt_dlp.YoutubeDL") as mock_ytdl:
            mock_inst = mock_ytdl.return_value
            mock_inst.__enter__.return_value = mock_inst
            tracks = await service.search_tracks("cached query")
            
            mock_inst.extract_info.assert_not_called()
            assert len(tracks) == 1
            assert tracks[0].title == "Cached Track"

    @pytest.mark.asyncio
    async def test_search_tracks_no_results(self, service):
        """Тест поиска без результатов."""
        with patch("yt_dlp.YoutubeDL") as mock_ytdl:
            mock_inst = mock_ytdl.return_value
            mock_inst.extract_info.return_value = None
            mock_inst.__enter__.return_value = mock_inst
            
            tracks = await service.search_tracks("nonexistent query")
            assert tracks == []
    
    @pytest.mark.asyncio
    async def test_search_tracks_error(self, service):
        """Тест обработки ошибки при поиске."""
        with patch("yt_dlp.YoutubeDL") as mock_ytdl:
            mock_inst = mock_ytdl.return_value
            mock_inst.extract_info.side_effect = Exception("Test error")
            mock_inst.__enter__.return_value = mock_inst
            
            tracks = await service.search_tracks("test query")
            assert tracks == []
    
    @pytest.mark.asyncio
    async def test_get_track_info_success(self, service):
        """Тест успешного получения информации о треке."""
        mock_data = {
            "title": "Test Track",
            "webpage_url": "https://youtube.com/watch?v=test",
            "duration": 180,
            "thumbnail": "https://example.com/thumb.jpg",
            "uploader": "Test Channel",
            "id": "test",
        }
        
        with patch.object(service.ytdl, 'extract_info', return_value=mock_data):
            track_info = await service.get_track_info("https://youtube.com/watch?v=test")
            
            assert track_info is not None
            assert track_info.title == "Test Track"
            assert track_info.duration == 180
            
    @pytest.mark.asyncio
    async def test_get_track_info_cache(self, service):
        """Тест кэша для информации о треке."""
        from src.schemas import TrackInfo
        cached_track = TrackInfo(
            title="Cached",
            raw_title="Cached",
            url="http://cached.url",
            duration=180,
            thumbnail="https://example.com/thumb.jpg",
            uploader="Test Uploader",
            id="cached"
        )
        service._info_cache["http://cached.url"] = cached_track
        
        with patch.object(service.ytdl, 'extract_info') as mock_extract:
            track_info = await service.get_track_info("http://cached.url")
            
            mock_extract.assert_not_called()
            assert track_info is not None
            assert track_info.title == "Cached"

    @pytest.mark.asyncio
    async def test_get_track_info_error(self, service):
        """Тест обработки ошибки при получении информации."""
        with patch.object(service.ytdl, 'extract_info', side_effect=Exception("Test error")):
            track_info = await service.get_track_info("https://youtube.com/watch?v=test")
            assert track_info is None
    
    @pytest.mark.asyncio
    async def test_get_audio_source_success(self, service):
        """Тест получения аудио-источника."""
        mock_source = MagicMock()
        mock_data = {
            "entries": [
                {
                    "url": "https://audio.stream.url",
                }
            ]
        }
        with patch("src.services.music_service.discord.FFmpegPCMAudio", return_value=mock_source) as mock_ffmpeg:
            with patch.object(service.ytdl, 'extract_info', return_value=mock_data):
                source = await service.get_audio_source("https://youtube.com/watch?v=test", start_time=10)
                
                assert source is not None
                assert source[0] is mock_source
                mock_ffmpeg.assert_called_once()
                args, kwargs = mock_ffmpeg.call_args
                assert args[0] == "https://audio.stream.url"
                assert "before_options" in kwargs
                assert "-ss 10" in kwargs["before_options"]

    @pytest.mark.asyncio
    async def test_get_audio_source_no_url(self, service):
        """Тест неудачного получения аудио-источника (нет url)."""
        mock_data = {"entries": [{"other": "data"}]}
        with patch.object(service.ytdl, 'extract_info', return_value=mock_data):
            source = await service.get_audio_source("https://youtube.com/watch?v=test")
            assert source is None

    @pytest.mark.asyncio
    async def test_get_audio_source_error(self, service):
        """Тест ошибки при получении аудио-источника."""
        with patch.object(service.ytdl, 'extract_info', side_effect=Exception("API error")):
            source = await service.get_audio_source("https://youtube.com/watch?v=test")
            assert source is None
    
    def test_format_duration(self, service):
        """Тест форматирования длительности."""
        assert service.format_duration(0) == "Неизвестно"
        assert service.format_duration(45) == "0:45"
        assert service.format_duration(125) == "2:05"
        assert service.format_duration(3665) == "1:01:05"

