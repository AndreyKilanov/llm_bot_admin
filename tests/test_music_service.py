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
        return MusicService()
    
    def test_singleton(self, service):
        """Тест паттерна Singleton."""
        another_service = MusicService()
        assert service is another_service
        assert service is music_service
    
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
        
        with patch.object(service.ytdl, 'extract_info', return_value=mock_data):
            tracks = await service.search_tracks("test query", max_results=2)
            
            assert len(tracks) == 2
            assert tracks[0]["title"] == "Test Track 1"
            assert tracks[0]["duration"] == 180
            assert tracks[1]["title"] == "Test Track 2"
    
    @pytest.mark.asyncio
    async def test_search_tracks_no_results(self, service):
        """Тест поиска без результатов."""
        with patch.object(service.ytdl, 'extract_info', return_value=None):
            tracks = await service.search_tracks("nonexistent query")
            assert tracks == []
    
    @pytest.mark.asyncio
    async def test_search_tracks_error(self, service):
        """Тест обработки ошибки при поиске."""
        with patch.object(service.ytdl, 'extract_info', side_effect=Exception("Test error")):
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
            assert track_info["title"] == "Test Track"
            assert track_info["duration"] == 180
    
    @pytest.mark.asyncio
    async def test_get_track_info_error(self, service):
        """Тест обработки ошибки при получении информации."""
        with patch.object(service.ytdl, 'extract_info', side_effect=Exception("Test error")):
            track_info = await service.get_track_info("https://youtube.com/watch?v=test")
            assert track_info is None
    
    def test_format_duration(self, service):
        """Тест форматирования длительности."""
        assert service.format_duration(0) == "Неизвестно"
        assert service.format_duration(45) == "0:45"
        assert service.format_duration(125) == "2:05"
        assert service.format_duration(3665) == "1:01:05"
