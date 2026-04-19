"""Сервис получения текста песни через бесплатный API lyrics.ovh."""

from __future__ import annotations

import logging
import re

import httpx

logger = logging.getLogger("services.lyrics")

_LYRICS_BASE_URL = "https://api.lyrics.ovh/v1/{artist}/{title}"
_MAX_LYRICS_LENGTH = 1900  # Лимит Discord embed description


class LyricsService:
    """Получение текста песни через бесплатный API lyrics.ovh.

    API не требует ключа и поддерживает большинство популярных треков.
    При превышении лимита Discord текст обрезается с многоточием.
    """

    async def get_lyrics(self, title: str, artist: str) -> str | None:
        """Получить текст трека.

        Args:
            title: Название трека.
            artist: Имя исполнителя.

        Returns:
            Текст песни или None если не найден / ошибка API.
        """
        clean_title = self._clean_query(title)
        clean_artist = self._clean_query(artist)
        url = _LYRICS_BASE_URL.format(artist=clean_artist, title=clean_title)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)

            if response.status_code == 404:
                logger.debug("Текст не найден: %s — %s", artist, title)
                return None

            response.raise_for_status()
            data = response.json()
            lyrics: str = data.get("lyrics", "")

            if not lyrics:
                return None

            if len(lyrics) > _MAX_LYRICS_LENGTH:
                lyrics = lyrics[:_MAX_LYRICS_LENGTH].rsplit("\n", 1)[0] + "\n…"

            return lyrics

        except httpx.HTTPStatusError as exc:
            logger.warning(
                "HTTP ошибка lyrics.ovh (%s — %s): %s",
                artist,
                title,
                exc.response.status_code,
            )
            return None
        except httpx.RequestError as exc:
            logger.error("Сетевая ошибка lyrics.ovh: %s", exc)
            return None
        except Exception as exc:
            logger.exception("Неожиданная ошибка LyricsService: %s", exc)
            return None

    @staticmethod
    def _clean_query(text: str) -> str:
        """Очистить строку для URL запроса.

        Удаляет лишние скобки, ремиксы и специальные символы из названия трека.

        Args:
            text: Исходная строка.

        Returns:
            Очищенная строка.
        """
        text = re.sub(r"\(.*?\)", "", text)
        text = re.sub(r"\[.*?\]", "", text)
        return text.strip()


lyrics_service = LyricsService()
