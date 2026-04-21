"""
Сервис для работы с музыкой из YouTube.

Этот модуль предоставляет функциональность для поиска и загрузки
аудио-треков из YouTube с использованием yt-dlp.
"""

import asyncio
import logging
import re
import httpx
import json
import re
from typing import Optional, TYPE_CHECKING
from urllib.parse import urlparse

import discord
from src.schemas import TrackInfo

if TYPE_CHECKING:
    pass
import yt_dlp

logger = logging.getLogger("music.service")


class MusicService:
    """
    Singleton-сервис для управления музыкальными операциями.
    
    Предоставляет методы для поиска треков на YouTube и получения
    аудио-потоков для воспроизведения в Discord.
    """
    
    _instance: Optional["MusicService"] = None

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
        "extract_flat": "in_playlist",
        "cachedir": False,
        "youtube_include_dash_manifest": False,
        "youtube_include_hls_manifest": False,
    }

    FFMPEG_OPTIONS = {
        "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 2 -reconnect_on_network_error 1 -reconnect_on_http_error 403,404,500,502,503,504 -reconnect_at_eof 1",
        "options": "-vn -sn -dn -af loudnorm=I=-16:TP=-1.5:LRA=11 -buffer_size 16M -nostats",
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
            
            fast_opts = self.YTDL_OPTIONS.copy()
            fast_opts["extract_flat"] = True
            self.ytdl_fast = yt_dlp.YoutubeDL(fast_opts)
            
            self._search_cache: dict[str, list[TrackInfo]] = {}
            self._info_cache: dict[str, TrackInfo] = {}
            self._initialized = True
            logger.info("MusicService инициализирован (Python 3.11+)")

    def is_valid_url(self, url: str) -> bool:
        """
        Проверка валидности YouTube URL.
        
        Args:
            url: URL для проверки
            
        Returns:
            True если URL корректный и относится к YouTube
        """
        try:
            parsed = urlparse(url)
            return parsed.netloc in ("www.youtube.com", "youtube.com", "m.youtube.com", "youtu.be")
        except Exception:
            return False
    
    async def search_tracks(
        self, 
        query: str, 
        max_results: int = 5,
        extract_flat: bool = False
    ) -> list[TrackInfo]:
        """
        Поиск треков на YouTube по запросу.
        
        Args:
            query: Поисковый запрос
            max_results: Максимальное количество результатов
            
        Returns:
            Список словарей с информацией о треках
        """
        query = query.strip()
        if not query:
            return []

        cache_key = f"{query}:{max_results}:{extract_flat}"
        if cache_key in self._search_cache:
            return self._search_cache[cache_key]

        logger.info(f"Поиск треков на YouTube: {query}")
        
        try:
            loop = asyncio.get_running_loop()
            process_query = f"ytsearch{max_results}:{query}"
            
            opts = self.YTDL_OPTIONS.copy()
            if extract_flat:
                opts["extract_flat"] = True
            
            def _extract():
                with yt_dlp.YoutubeDL(opts) as ydl:
                    return ydl.extract_info(process_query, download=False)

            data = await loop.run_in_executor(None, _extract)
            
            if not data or "entries" not in data:
                logger.warning(f"YouTube не вернул результатов для запроса: {query}")
                return []
            
            tracks = []
            for entry in data["entries"]:
                if not entry:
                    continue
                    
                track_info = TrackInfo(
                    title=self.clean_title(entry.get("title") or "Неизвестно"),
                    raw_title=entry.get("title") or "Неизвестно",
                    url=entry.get("webpage_url") or entry.get("url", ""),
                    duration=entry.get("duration") or 0,
                    thumbnail=entry.get("thumbnail") or "",
                    uploader=entry.get("uploader") or "Неизвестно",
                    id=entry.get("id", ""),
                    view_count=entry.get("view_count") or 0,
                )
                tracks.append(track_info)
                
                if track_info.url:
                    self._info_cache[str(track_info.url)] = track_info

            if any(t.view_count for t in tracks):
                tracks.sort(key=lambda x: x.view_count, reverse=True)
            
            logger.info(f"Найдено треков для '{query}': {len(tracks)}")
            self._search_cache[cache_key] = tracks
            return tracks
            
        except Exception as e:
            logger.error(f"Ошибка при поиске треков '{query}': {e}", exc_info=True)
            return []

    async def get_search_suggestions(self, query: str) -> list[str]:
        """
        Получение поисковых подсказок через Google Suggest API (очень быстро).
        """
        if not query.strip():
            return []
            
        url = "https://suggestqueries.google.com/complete/search"
        params = {
            "client": "firefox",
            "ds": "yt",
            "q": query
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=1.5)
                if response.status_code == 200:
                    data = response.json()
                    suggestions = data[1]
                    logger.debug(f"Получено подсказок для '{query}': {len(suggestions)}")
                    return suggestions
                else:
                    logger.warning(f"Suggest API вернул статус {response.status_code}")
        except Exception as e:
            logger.warning(f"Ошибка при получении подсказок: {e}")
            
        return []

    async def search_tracks_fast(self, query: str, max_results: int = 10) -> list[TrackInfo]:
        """
        Сверхбыстрый парсинг поисковой выдачи YouTube для автокомплита (в обход медленного yt-dlp).
        """
        query = query.strip()
        if not query:
            return []

        url = "https://www.youtube.com/results"
        params = {"search_query": query}
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, headers=headers, timeout=1.5)
                html = response.text
                
            match = re.search(r"var ytInitialData = ({.*?});</script>", html)
            if not match:
                return []
                
            data = json.loads(match.group(1))
            contents = data.get("contents", {}).get("twoColumnSearchResultsRenderer", {}).get("primaryContents", {}).get("sectionListRenderer", {}).get("contents", [])
            
            if not contents:
                return []
                
            item_section = next((item for item in contents if "itemSectionRenderer" in item), None)
            if not item_section:
                return []
                
            video_items = item_section["itemSectionRenderer"].get("contents", [])
            
            tracks = []
            for item in video_items:
                if "videoRenderer" in item:
                    video = item["videoRenderer"]
                    title = video.get("title", {}).get("runs", [{}])[0].get("text", "Неизвестно")
                    video_id = video.get("videoId", "")
                    if not video_id:
                        continue
                        
                    uploader = video.get("ownerText", {}).get("runs", [{}])[0].get("text", "YouTube")
                    url = f"https://www.youtube.com/watch?v={video_id}"
                    
                    track_info = TrackInfo(
                        title=self.clean_title(title),
                        raw_title=title,
                        url=url,
                        uploader=uploader,
                        id=video_id
                    )
                    tracks.append(track_info)
                    
                    self._info_cache[url] = track_info
                    
                    if len(tracks) >= max_results:
                        break
                        
            return tracks
            
        except Exception as e:
            logger.error(f"Ошибка в search_tracks_fast: {e}")
            return []
            
    
    async def get_track_info(self, url: str) -> Optional[TrackInfo]:
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
            
            if "entries" in data:
                if not data["entries"]:
                    return None
                data = data["entries"][0]

            info = TrackInfo(
                title=data.get("title") or "Неизвестно",
                raw_title=data.get("title") or "Неизвестно",
                url=data.get("webpage_url") or data.get("url", ""),
                duration=data.get("duration") or 0,
                thumbnail=data.get("thumbnail") or "",
                uploader=data.get("uploader") or "Неизвестно",
                id=data.get("id", ""),
            )
            
            self._info_cache[url] = info
            return info
            
        except Exception as e:
            logger.error(f"Ошибка при получении информации о треке: {e}", exc_info=True)
            return None

    async def get_playlist_info(self, url: str) -> list[TrackInfo]:
        """
        Получение списка треков из плейлиста YouTube.
        
        Args:
            url: URL плейлиста на YouTube
            
        Returns:
            Список словарей с информацией о треках
        """
        logger.info(f"Получение информации о плейлисте: {url}")
        
        try:
            opts = self.YTDL_OPTIONS.copy()
            opts["noplaylist"] = False
            
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None,
                lambda: yt_dlp.YoutubeDL(opts).extract_info(url, download=False)
            )

            
            if not data or "entries" not in data:
                logger.warning(f"Плейлист пуст или не найден: {url}")
                return []
            
            tracks = []
            for entry in data["entries"]:
                if entry:
                    track_info = TrackInfo(
                        title=self.clean_title(entry.get("title") or "Неизвестно"),
                        raw_title=entry.get("title") or "Неизвестно",
                        url=entry.get("webpage_url") or entry.get("url", ""),
                        duration=entry.get("duration") or 0,
                        thumbnail=entry.get("thumbnail") or "",
                        uploader=entry.get("uploader") or "Неизвестно",
                        id=entry.get("id", ""),
                    )
                    tracks.append(track_info)
                    if track_info.url:
                        self._info_cache[str(track_info.url)] = track_info

            logger.info(f"Загружено треков из плейлиста: {len(tracks)}")
            return tracks
            
        except Exception as e:
            logger.error(f"Ошибка при получении плейлиста: {e}", exc_info=True)
            return []
    
    async def get_audio_source(self, url: str, start_time: int = 0):
        """
        Получение аудио-потока для воспроизведения в Discord.
        """
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
                ffmpeg_options["before_options"] = f"{ffmpeg_options['before_options']} -ss {int(start_time)}"
                
            source = discord.FFmpegPCMAudio(audio_url, **ffmpeg_options)
            logger.info(f"Аудио-поток создан (позиция: {int(start_time)}с)")

            return source
            
        except (yt_dlp.utils.DownloadError, yt_dlp.utils.ExtractorError) as e:
            logger.warning(f"Трек недоступен (приватный или удален): {url}. Ошибка: {e}")
            return None
        except Exception as e:
            logger.error(f"Ошибка при создании аудио-потока: {e}", exc_info=True)
            return None
    
    def clean_title(self, title: str) -> str:
        """
        Очистка названия трека от лишнего мусора с помощью regex.
        
        Удаляет: [Official Video], (Lyrics), HD, 4K и т.д.
        """
        if not title:
            return "Неизвестно"
            
        # Паттерны для удаления (регистронезависимые)
        patterns = [
            r"(?i)\[.*?\]",                                     # Все в квадратных скобках [HD], [Official]
            r"(?i)\(.*?视频.*?\)",                               # Китайские метаданные (часто в YouTube Music)
            r"(?i)\(official (video|audio|lyric|visualizer)\)", # (Official Video), (Official Audio)
            r"(?i)\(lyrics?\)",                                  # (Lyrics), (Lyric)
            r"(?i)\(ft\..*?\)",                                  # (ft. Artist) - опционально, но часто лучше оставить
            r"(?i)\b(official (video|audio|lyric|visualizer)|lyric video|original mix|extended mix|remastered)\b",
            r"(?i)\b(hd|4k|1080p|hq)\b",                         # Качество
        ]
        
        clean_title = title
        for pattern in patterns:
            clean_title = re.sub(pattern, "", clean_title)
            
        # Удаляем пустые скобки, если остались
        clean_title = re.sub(r"\(\s*\)", "", clean_title)
        clean_title = re.sub(r"\[\s*\]", "", clean_title)
        
        # Нормализуем пробелы
        clean_title = re.sub(r"\s+", " ", clean_title).strip()
        
        # Если после очистки ничего не осталось, возвращаем оригинал (на всякий случай)
        return clean_title if len(clean_title) > 2 else title

    def format_duration(self, seconds: int) -> str:
        """
        Форматирование длительности трека.
        
        Args:
            seconds: Длительность в секундах
            
        Returns:
            Отформатированная строка (например, "3:45" или "1:23:45")
        """
        if not seconds:
            return "Неизвестно"
        
        try:
            seconds_val = int(seconds)
        except (TypeError, ValueError):
            return "Неизвестно"

        if seconds_val <= 0:
            return "Неизвестно"
        
        hours = seconds_val // 3600
        minutes = (seconds_val % 3600) // 60
        secs = seconds_val % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"

music_service = MusicService()
