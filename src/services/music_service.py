"""
Сервис для работы с музыкой из YouTube.

Этот модуль предоставляет функциональность для поиска и загрузки
аудио-треков из YouTube с использованием yt-dlp.
"""

import asyncio
import logging
from typing import Optional, TYPE_CHECKING

# Ленивый импорт discord для избежания зависимости при использовании только Telegram
if TYPE_CHECKING:
    import discord
import yt_dlp

logger = logging.getLogger("music.service")


class MusicService:
    """
    Singleton-сервис для управления музыкальными операциями.
    
    Предоставляет методы для поиска треков на YouTube и получения
    аудио-потоков для воспроизведения в Discord.
    """
    
    _instance: Optional["MusicService"] = None

    # Настройки для ускорения извлечения данных
    YTDL_OPTIONS = {
        "format": "bestaudio/best",
        "extractaudio": True,
        "audioformat": "mp3",
        "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
        "restrictfilenames": True,
        "noplaylist": True,
        "nocheckcertificate": True,
        "ignoreerrors": False,
        "logtostderr": False,
        "quiet": True,
        "no_warnings": True,
        "default_search": "ytsearch",
        "source_address": "0.0.0.0",
        "extract_flat": "in_playlist",  # Ускоряет извлечение метаданных
        "cachedir": False,
        "youtube_include_dash_manifest": False,
        "youtube_include_hls_manifest": False,
    }

    FFMPEG_OPTIONS = {
        "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        "options": "-vn",
    }
    
    def __new__(cls) -> "MusicService":
        """Реализация паттерна Singleton."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Инициализация сервиса."""
        if not hasattr(self, "_initialized"):
            self.ytdl = yt_dlp.YoutubeDL(self.YTDL_OPTIONS)
            self._search_cache: dict[str, list[dict]] = {}
            self._info_cache: dict[str, dict] = {}
            self._initialized = True
            logger.info("MusicService инициализирован (с кэшированием метаданных)")

    def is_valid_url(self, url: str) -> bool:
        """
        Проверка валидности YouTube URL.
        
        Args:
            url: URL для проверки
            
        Returns:
            True если URL корректный и относится к YouTube
        """
        from urllib.parse import urlparse
        try:
            parsed = urlparse(url)
            return parsed.netloc in ("www.youtube.com", "youtube.com", "m.youtube.com", "youtu.be")
        except:
            return False
    
    async def search_tracks(
        self, 
        query: str, 
        max_results: int = 5
    ) -> list[dict]:
        """
        Поиск треков на YouTube по запросу.
        
        Args:
            query: Поисковый запрос
            max_results: Максимальное количество результатов
            
        Returns:
            Список словарей с информацией о треках
        """
        cache_key = f"{query}:{max_results}"
        if cache_key in self._search_cache:
            logger.info(f"Получение из кэша поиска: {query}")
            return self._search_cache[cache_key]

        logger.info(f"Поиск треков: {query}")
        
        try:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None,
                lambda: self.ytdl.extract_info(
                    f"ytsearch{max_results}:{query}",
                    download=False
                )
            )
            
            if not data or "entries" not in data:
                logger.warning(f"Треки не найдены для запроса: {query}")
                return []
            
            tracks = []
            for entry in data["entries"]:
                if entry:
                    track_info = {
                        "title": entry.get("title", "Неизвестно"),
                        "url": entry.get("webpage_url") or entry.get("url", ""),
                        "duration": entry.get("duration", 0),
                        "thumbnail": entry.get("thumbnail", ""),
                        "uploader": entry.get("uploader", "Неизвестно"),
                        "id": entry.get("id", ""),
                    }
                    tracks.append(track_info)
                    if track_info["url"]:
                        self._info_cache[track_info["url"]] = track_info

            self._search_cache[cache_key] = tracks
            logger.info(f"Найдено треков: {len(tracks)}")
            return tracks
            
        except Exception as e:
            logger.error(f"Ошибка при поиске треков: {e}", exc_info=True)
            return []
    
    async def get_track_info(self, url: str) -> Optional[dict]:
        """
        Получение информации о треке по URL.
        
        Args:
            url: URL трека на YouTube
            
        Returns:
            Словарь с информацией о треке или None при ошибке
        """
        if url in self._info_cache:
            return self._info_cache[url]

        logger.info(f"Получение информации о треке: {url}")
        
        try:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None,
                lambda: self.ytdl.extract_info(url, download=False)
            )
            
            if not data:
                return None
            
            info = {
                "title": data.get("title", "Неизвестно"),
                "url": data.get("webpage_url") or data.get("url", ""),
                "duration": data.get("duration", 0),
                "thumbnail": data.get("thumbnail", ""),
                "uploader": data.get("uploader", "Неизвестно"),
                "id": data.get("id", ""),
            }
            
            self._info_cache[url] = info
            return info
            
        except Exception as e:
            logger.error(f"Ошибка при получении информации о треке: {e}", exc_info=True)
            return None
    
    async def get_audio_source(self, url: str, start_time: int = 0):
        """
        Получение аудио-потока для воспроизведения в Discord.
        """
        import discord
        
        logger.info(f"Получение свежего аудио-потока: {url} (с {start_time}с)")
        
        try:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None,
                lambda: self.ytdl.extract_info(url, download=False)
            )
            
            if not data:
                logger.error("Не удалось получить данные трека")
                return None

            if "entries" in data:
                data = data["entries"][0]
            
            audio_url = data.get("url")
            if not audio_url:
                logger.error("URL аудио-потока не найден")
                return None
            
            ffmpeg_options = self.FFMPEG_OPTIONS.copy()
            if start_time > 0:
                ffmpeg_options["options"] = f"{ffmpeg_options['options']} -ss {int(start_time)}"
                
            source = discord.FFmpegPCMAudio(audio_url, **ffmpeg_options)
            logger.info(f"Аудио-поток создан (позиция: {int(start_time)}с)")

            return source
            
        except Exception as e:
            logger.error(f"Ошибка при создании аудио-потока: {e}", exc_info=True)
            return None
    
    def format_duration(self, seconds: int) -> str:
        """
        Форматирование длительности трека.
        
        Args:
            seconds: Длительность в секундах
            
        Returns:
            Отформатированная строка (например, "3:45" или "1:23:45")
        """
        if seconds == 0:
            return "Неизвестно"
        
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"

music_service = MusicService()
