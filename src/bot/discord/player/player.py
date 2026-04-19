from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Final

import discord
from src.services import music_service
from .enums import LoopMode
from .queue_manager import QueueManager, TrackData
from .voice_handler import VoiceHandler

if TYPE_CHECKING:
    from discord import Client, Message, TextChannel, VoiceChannel, VoiceClient

logger = logging.getLogger("discord.music_player")

DEFAULT_DISCONNECT_DELAY: Final[int] = 600
PLAYLIST_CLEAR_TIMEOUT: Final[int] = 1800
UI_UPDATE_DELAY: Final[float] = 0.1


class MusicPlayer:
    """Главный класс-фасад для управления музыкальным плеером на сервере."""

    def __init__(self, guild_id: int, bot: Client) -> None:
        """Инициализация музыкального плеера.

        Args:
            guild_id: ID сервера.
            bot: Экземпляр бота.
        """
        self.guild_id = guild_id
        self.bot = bot
        
        self.queue_manager = QueueManager()
        self.voice_handler = VoiceHandler(guild_id, bot)
        
        self.is_playing: bool = False
        self.is_paused: bool = False

        self._volume: float = 1.0
        self._is_muted: bool = False
        self._pre_mute_volume: float = 1.0
        self._current_source: discord.PCMVolumeTransformer | None = None

        self.start_time: float | None = None
        self.pause_time: float | None = None
        self.paused_duration: float = 0.0
        
        self.player_view: any = None
        self.player_message: Message | None = None
        self.text_channel: TextChannel | None = None
        
        self._play_lock: asyncio.Lock = asyncio.Lock()
        self._disconnect_task: asyncio.Task | None = None
        self._playlist_clear_task: asyncio.Task | None = None
        self._preload_task: asyncio.Task | None = None

        logger.info("MusicPlayer инициализирован для сервера %d", guild_id)

    # ==================== Прокси-свойства для удобства ====================
    
    @property
    def queue(self) -> list[TrackData]:
        return self.queue_manager.queue

    @property
    def current_track(self) -> TrackData | None:
        return self.queue_manager.current_track

    @current_track.setter
    def current_track(self, value: TrackData | None) -> None:
        self.queue_manager.current_track = value

    @property
    def current_index(self) -> int:
        return self.queue_manager.current_index

    @current_index.setter
    def current_index(self, value: int) -> None:
        self.queue_manager.current_index = value

    @property
    def loop_mode(self) -> LoopMode:
        return self.queue_manager.loop_mode

    @loop_mode.setter
    def loop_mode(self, value: LoopMode) -> None:
        self.queue_manager.loop_mode = value

    @property
    def voice_client(self) -> VoiceClient | None:
        return self.voice_handler.voice_client

    @property
    def is_connected(self) -> bool:
        return self.voice_handler.is_connected

    # ==================== Публичные методы управления ====================

    async def connect(self, channel: VoiceChannel) -> bool:
        was_connected = self.is_connected
        success = await self.voice_handler.connect(channel)
        
        if success and not was_connected:
            self._volume = 1.0
            self._is_muted = False
            logger.info("Громкость сброшена до 100%% при входе в канал на сервере %d", self.guild_id)

        if success and not self.is_playing:
            self._schedule_disconnect()
        return success

    async def disconnect(self) -> None:
        await self.stop()
        await self.voice_handler.disconnect()
        self._cancel_tasks()

    def add_to_queue(self, tracks: list[TrackData]) -> None:
        self.queue_manager.add(tracks)

    async def play_next(self) -> bool:
        async with self._play_lock:
            track = self.queue_manager.get_next_track()
            if not track:
                return False
            return await self._play_track(track)

    async def play_previous(self) -> bool:
        async with self._play_lock:
            track = self.queue_manager.get_previous_track()
            if not track:
                return False
            return await self._play_track(track)

    async def play_at_index(self, index: int) -> bool:
        """Воспроизвести трек по указанному индексу в очереди.

        Args:
            index: Индекс трека (0-based).

        Returns:
            bool: True если воспроизведение запущено, иначе False.
        """
        async with self._play_lock:
            if index < 0 or index >= len(self.queue):
                return False
            
            track = self.queue[index]
            self.queue_manager.current_index = index
            return await self._play_track(track)

    async def play_from_start(self) -> bool:
        """Начать воспроизведение с первого трека в очереди."""
        async with self._play_lock:
            if not self.queue:
                return False
            self.queue_manager.reset_index()
            self.queue_manager.current_index = 0
            return await self._play_track(self.queue[0])

    def pause(self) -> bool:
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.pause()
            self.is_paused = True
            self.pause_time = time.time()
            logger.info("Пауза на сервере %d", self.guild_id)
            self._schedule_disconnect()
            return True
        return False

    def resume(self) -> bool:
        if self.voice_client and self.voice_client.is_paused():
            self.voice_client.resume()
            self.is_paused = False
            self.is_playing = True
            if self.pause_time:
                self.paused_duration += time.time() - self.pause_time
                self.pause_time = None
            logger.info("Возобновление на сервере %d", self.guild_id)
            self._cancel_tasks()
            return True
        return False

    async def stop(self) -> None:
        self.voice_handler.stop_vc()
        self.queue_manager.clear()
        self._reset_playback_state()
        await self.clear_player_ui()
        logger.info("Остановка и очистка на сервере %d", self.guild_id)
        self._schedule_disconnect()

    async def stop_playback(self) -> None:
        self.voice_handler.stop_vc()
        self._reset_playback_state()
        self.queue_manager.reset_index()
        logger.info("Остановка (без очистки) на сервере %d", self.guild_id)
        self._schedule_disconnect()
        self._schedule_playlist_clear()

    async def seek_relative(self, seconds: int) -> bool:
        if not self.current_track or not self.start_time:
            return False
        
        async with self._play_lock:
            current_pos, total_dur = self.get_playback_position()
            new_pos = max(0, min(current_pos + seconds, total_dur))
            if new_pos == current_pos:
                return False
            
            try:
                url = str(self.current_track.get("url", ""))
                new_source = await music_service.get_audio_source(url, start_time=new_pos)
                if not new_source:
                    return False
                
                vc = self.voice_client
                if vc:
                    self.voice_handler.manual_skip = True
                    vc.stop()
                    await asyncio.sleep(UI_UPDATE_DELAY)
                    
                    now = time.time()
                    self.start_time = now - new_pos
                    self.paused_duration = 0
                    if self.is_paused:
                        self.pause_time = now
                    
                    vc.play(new_source, after=lambda e: self._after_playing_callback(e, vc))
                    self.is_playing = True
                    if self.is_paused:
                        vc.pause()
                    
                    await self._update_player_ui()
                    return True
            except Exception as e:
                logger.error("Ошибка перемотки на сервере %d: %s", self.guild_id, e)
        return False

    def get_playback_position(self) -> tuple[int, int]:
        if not self.current_track or not self.start_time:
            return (0, 0)
        
        duration = int(self.current_track.get("duration", 0))
        if self.is_paused and self.pause_time:
            elapsed = self.pause_time - self.start_time - self.paused_duration
        else:
            elapsed = time.time() - self.start_time - self.paused_duration

        return (min(int(elapsed), duration), duration)

    def cycle_loop_mode(self) -> LoopMode:
        mode = self.queue_manager.cycle_loop_mode()
        logger.info("Режим зацикливания сервера %d: %s", self.guild_id, mode)
        return mode

    def shuffle_queue(self) -> None:
        """Перемешать очередь сохраняя текущий трек."""
        self.queue_manager.shuffle()
        logger.info("Очередь перемешана на сервере %d", self.guild_id)

    def set_volume(self, volume: float) -> None:
        """Установить громкость воспроизведения без перезапуска трека.

        Args:
            volume: Громкость от 0.0 до 1.0 (1.0 = 100%).
        """
        self._volume = max(0.0, min(volume, 1.0))
        if self._current_source is not None:
            self._current_source.volume = self._volume
        logger.info("Громкость на сервере %d: %.0f%%", self.guild_id, self._volume * 100)

    def toggle_mute(self) -> bool:
        """Переключить заглушку.

        Returns:
            True — заглушено, False — звук включён.
        """
        if self._is_muted:
            self._is_muted = False
            self.set_volume(self._pre_mute_volume)
        else:
            self._pre_mute_volume = self._volume
            self._is_muted = True
            self.set_volume(0.0)
        logger.info("Mute на сервере %d: %s", self.guild_id, self._is_muted)
        return self._is_muted

    @property
    def volume(self) -> float:
        """Текущая громкость (0.0–1.0)."""
        return self._volume

    @property
    def is_muted(self) -> bool:
        """Флаг заглушки."""
        return self._is_muted

    async def stop_playback_only(self) -> None:
        """Остановить воспроизведение без отключения и без очистки очереди.

        Бот остаётся в голосовом канале, очередь сохраняется.
        """
        self.voice_handler.stop_vc()
        self._reset_playback_state()
        self._current_source = None
        logger.info("Стоп (без отключения) на сервере %d. Очередь сохранена.", self.guild_id)

    def set_text_channel(self, channel: TextChannel) -> None:
        """Установить канал для текстовых уведомлений.

        Args:
            channel: Текстовый канал.
        """
        self.text_channel = channel

    def get_queue_info(self) -> dict:
        """Получить сводную информацию об очереди.

        Returns:
            dict: Словарь с данными очереди (треки, индекс, общее кол-во).
        """
        return {
            'tracks': self.queue,
            'current_index': self.current_index,
            'total': len(self.queue),
            'current_track': self.current_track,
            'loop_mode': self.loop_mode
        }

    # ==================== Внутренняя логика ====================

    async def _play_track(self, track: TrackData, retry_count: int = 0, is_retry: bool = False) -> bool:
        if not self.is_connected:
            return False

        if retry_count >= 5:
            logger.error("Слишком много ошибок воспроизведения подряд. Остановка.")
            await self._notify_error("❌ Слишком много ошибок в очереди. Воспроизведение остановлено.")
            await self.stop_playback()
            return False

        vc: VoiceClient = self.voice_client
        try:
            self.voice_handler.stop_vc()
            await asyncio.sleep(UI_UPDATE_DELAY)

            title = track.get("title", "Unknown")
            url = str(track.get("url", ""))
            
            logger.info("Воспроизведение трека на сервере %d: %s", self.guild_id, title)
            audio_source = await music_service.get_audio_source(url)

            if not audio_source:
                if not is_retry:
                    logger.warning("Не удалось получить аудио-поток для сервера %d. Пробую еще раз...", self.guild_id)
                    await asyncio.sleep(1)
                    return await self._play_track(track, retry_count, is_retry=True)
                
                await self._notify_error(f"⚠️ Трек **{title}** недоступен (приватный или удален). Пропускаю...")
                return await self._skip_to_next_on_error(retry_count)

            self.queue_manager.current_track = track
            self.is_playing = True
            self.is_paused = False
            self.start_time = time.time()
            self.pause_time = None
            self.paused_duration = 0.0

            self._cancel_tasks()

            volume_source = discord.PCMVolumeTransformer(audio_source, volume=self._volume)
            self._current_source = volume_source

            vc.play(volume_source, after=lambda e: self._after_playing_callback(e, vc))
            
            if self._preload_task:
                self._preload_task.cancel()
            self._preload_task = asyncio.create_task(self._preload_next())
            
            await self._update_player_ui()
            return True

        except Exception as e:
            logger.error("Ошибка воспроизведения на сервере %d: %s", self.guild_id, e)
            if not is_retry:
                logger.info("Повторная попытка воспроизведения трека %s после ошибки...", track.get('title'))
                await asyncio.sleep(1)
                return await self._play_track(track, retry_count, is_retry=True)
                
            await self._notify_error(f"⚠️ Ошибка при загрузке трека **{track.get('title')}**.")
            return await self._skip_to_next_on_error(retry_count)

    async def _skip_to_next_on_error(self, retry_count: int) -> bool:
        """Вспомогательный метод для корректного пропуска битого трека."""
        next_track = self.queue_manager.get_next_track()
        if next_track:
            return await self._play_track(next_track, retry_count + 1)
        
        logger.info("Очередь сервера %d пуста после пропуска ошибок", self.guild_id)
        await self._update_player_ui()
        self._schedule_disconnect()
        return False

    def _after_playing_callback(self, error: Exception | None, vc: VoiceClient) -> None:
        if error:
            logger.error("Ошибка потока на сервере %d: %s", self.guild_id, error)
        asyncio.run_coroutine_threadsafe(self._handle_track_end(), vc.loop)

    async def _handle_track_end(self) -> None:
        self.is_playing = False
        if self.voice_handler.manual_skip:
            self.voice_handler.manual_skip = False
            return

        if not await self.play_next():
            logger.info("Очередь сервера %d пуста", self.guild_id)
            await self._update_player_ui()
            self._schedule_disconnect()
            self._schedule_playlist_clear()

    async def _preload_next(self) -> None:
        try:
            if self.current_index + 1 < len(self.queue):
                next_track = self.queue[self.current_index + 1]
                await music_service.get_track_info(str(next_track.get("url", "")))
        except Exception as e:
            logger.error("Ошибка предзагрузки на сервере %d: %s", self.guild_id, e)

    async def _notify_error(self, message: str) -> None:
        if self.text_channel:
            try:
                await self.text_channel.send(message, delete_after=10.0)
            except Exception:
                pass

    def _reset_playback_state(self) -> None:
        self.is_playing = False
        self.is_paused = False
        self.start_time = None
        self.pause_time = None
        self.paused_duration = 0.0

    def _cancel_tasks(self) -> None:
        for task in [self._disconnect_task, self._playlist_clear_task]:
            if task:
                task.cancel()

    def _schedule_disconnect(self) -> None:
        if self._disconnect_task:
            self._disconnect_task.cancel()

        async def _delay() -> None:
            await asyncio.sleep(DEFAULT_DISCONNECT_DELAY)
            if not self.is_playing or self.is_paused:
                logger.info("Таймаут простоя (10 мин) на сервере %d. Отключение.", self.guild_id)
                await self.disconnect()

        self._disconnect_task = asyncio.create_task(_delay())

    def _schedule_playlist_clear(self) -> None:
        if self._playlist_clear_task:
            self._playlist_clear_task.cancel()

        async def _delay() -> None:
            await asyncio.sleep(PLAYLIST_CLEAR_TIMEOUT)
            if not self.is_playing or self.is_paused:
                logger.info("Таймаут хранения очереди (30 мин) на сервере %d. Очистка.", self.guild_id)
                self.queue_manager.clear()
                await self._update_player_ui()

        self._playlist_clear_task = asyncio.create_task(_delay())

    async def _update_player_ui(self) -> None:
        if self.text_channel and self.player_view:
            try:
                await self.player_view.update_player_message()
            except Exception as e:
                logger.warning("Не удалось обновить UI плеера на сервере %d: %s", self.guild_id, e)

    async def clear_player_ui(self) -> None:
        if self.player_view and hasattr(self.player_view, 'stop_auto_update'):
            self.player_view.stop_auto_update()
            
        if self.player_message:
            try:
                await self.player_message.delete()
            except Exception:
                pass
            self.player_message = None
            self.player_view = None
