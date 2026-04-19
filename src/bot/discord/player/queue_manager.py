from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING, TypeAlias

from .enums import LoopMode

if TYPE_CHECKING:
    from .enums import LoopMode

TrackData: TypeAlias = dict[str, str | int | float | None]

logger = logging.getLogger("discord.music_player.queue")


class QueueManager:
    """Класс для управления очередью воспроизведения треков."""

    def __init__(self) -> None:
        """Инициализация менеджера очереди."""
        self._queue: list[TrackData] = []
        self._current_index: int = -1
        self._loop_mode: LoopMode = LoopMode.NONE
        self._current_track: TrackData | None = None

    @property
    def queue(self) -> list[TrackData]:
        """Список всех треков в очереди."""
        return self._queue

    @property
    def current_index(self) -> int:
        """Индекс текущего трека."""
        return self._current_index

    @current_index.setter
    def current_index(self, value: int) -> None:
        self._current_index = value

    @property
    def current_track(self) -> TrackData | None:
        """Текущий воспроизводимый трек."""
        return self._current_track

    @current_track.setter
    def current_track(self, value: TrackData | None) -> None:
        self._current_track = value

    @property
    def loop_mode(self) -> LoopMode:
        """Текущий режим зацикливания."""
        return self._loop_mode

    @loop_mode.setter
    def loop_mode(self, value: LoopMode) -> None:
        self._loop_mode = value

    def add(self, tracks: list[TrackData]) -> None:
        """Добавить треки в очередь.

        Args:
            tracks: Список треков.
        """
        self._queue.extend(tracks)
        logger.debug("Добавлено %d треков. Очередь: %d", len(tracks), len(self._queue))

    def clear(self) -> None:
        """Очистить очередь и сбросить состояние."""
        self._queue.clear()
        self._current_index = -1
        self._current_track = None
        logger.debug("Очередь очищена")

    def get_next_track(self) -> TrackData | None:
        """Получить следующий трек с учетом режима зацикливания.

        Returns:
            Словарь с данными трека или None, если очередь завершена.
        """
        if self._loop_mode == LoopMode.TRACK and self._current_track:
            return self._current_track

        if self._current_index + 1 >= len(self._queue):
            if self._loop_mode == LoopMode.PLAYLIST and self._queue:
                self._current_index = 0
                return self._queue[0]
            return None

        self._current_index += 1
        return self._queue[self._current_index]

    def get_previous_track(self) -> TrackData | None:
        """Получить предыдущий трек.

        Returns:
            Словарь с данными трека или None, если это первый трек.
        """
        if self._current_index <= 0:
            return None

        self._current_index -= 1
        return self._queue[self._current_index]

    def reset_index(self) -> None:
        """Сбросить индекс (например, для начала воспроизведения с начала)."""
        self._current_index = -1

    def cycle_loop_mode(self) -> LoopMode:
        """Переключить режим зацикливания по кругу.

        Returns:
            Новый режим зацикливания.
        """
        match self._loop_mode:
            case LoopMode.NONE:
                self._loop_mode = LoopMode.TRACK
            case LoopMode.TRACK:
                self._loop_mode = LoopMode.PLAYLIST
            case LoopMode.PLAYLIST:
                self._loop_mode = LoopMode.NONE

        return self._loop_mode

    def shuffle(self) -> None:
        """Перемешать очередь случайным образом.

        Текущий воспроизводимый трек остаётся на своей позиции (current_index).
        Все остальные треки перемешиваются случайно.
        """
        if len(self._queue) <= 1:
            logger.debug("Перемешивание не выполнено: очередь содержит менее 2 треков")
            return

        current = (
            self._queue[self._current_index]
            if 0 <= self._current_index < len(self._queue)
            else None
        )

        if current is not None:
            remaining = [t for i, t in enumerate(self._queue) if i != self._current_index]
            random.shuffle(remaining)
            self._queue = [current] + remaining
            self._current_index = 0
        else:
            random.shuffle(self._queue)

        logger.info("Очередь перемешана (%d треков)", len(self._queue))
