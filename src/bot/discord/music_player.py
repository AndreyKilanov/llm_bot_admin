import asyncio
import logging
import time
from typing import Optional

import discord

from src.services.music_service import music_service

logger = logging.getLogger("discord.music_player")


class MusicPlayer:
    """
    Класс для управления воспроизведением музыки в голосовом канале Discord.
    
    Каждый экземпляр класса управляет воспроизведением для одного сервера.
    Поддерживает очередь треков, переключение, паузу и другие операции.
    """
    
    def __init__(self, guild_id: int, bot: discord.Client):
        """
        Инициализация плеера для конкретного сервера.

        Args:
            guild_id: ID сервера Discord
            bot: Экземпляр бота (для получения guild)
        """
        self.guild_id = guild_id
        self.bot = bot
        self._voice_channel: Optional[discord.VoiceChannel] = None
        self.queue: list[dict] = []
        self.current_track: Optional[dict] = None
        self.current_index: int = -1
        self.is_playing: bool = False
        self.is_paused: bool = False
        self._play_lock = asyncio.Lock()
        self._disconnect_task: Optional[asyncio.Task] = None
        self._voice_channel: Optional[discord.VoiceChannel] = None
        self._manual_skip: bool = False
        self.player_view = None
        self.player_message = None
        self.text_channel = None
        self.start_time: Optional[float] = None
        self.pause_time: Optional[float] = None
        self.paused_duration: float = 0.0

        logger.info(f"MusicPlayer создан для сервера {guild_id}")

    @property
    def voice_client(self) -> Optional[discord.VoiceClient]:
        """Получить актуальный VoiceClient для гильдии."""
        guild = self.bot.get_guild(self.guild_id)
        if guild:
            return guild.voice_client
        return None

    @property
    def is_connected(self) -> bool:
        """Проверить, подключен ли бот к голосовому каналу."""
        vc = self.voice_client
        return vc is not None and vc.is_connected()

    async def _schedule_disconnect(self):
        """Запланировать отключение через 10 минут бездействия."""
        if self._disconnect_task:
            self._disconnect_task.cancel()

        async def disconnect_after_delay():
            await asyncio.sleep(600)  # 10 минут
            if not self.is_playing and not self.is_paused:
                await self.disconnect()

        self._disconnect_task = asyncio.create_task(disconnect_after_delay())

    async def connect(self, channel: discord.VoiceChannel) -> bool:
        """
        Подключение к голосовому каналу.
        
        Args:
            channel: Голосовой канал для подключения
            
        Returns:
            True если подключение успешно, False иначе
        """
        self._voice_channel = channel

        guild = self.bot.get_guild(self.guild_id)
        if not guild:
            logger.error("Гильдия не найдена")
            return False

        if guild.voice_client and guild.voice_client.is_connected():
            if guild.voice_client.channel.id == channel.id:
                logger.info(f"Уже подключен к каналу {channel.name}")
                return True

            await guild.voice_client.move_to(channel)
            logger.info(f"Переключен на канал {channel.name}")
            return True

        try:
            await channel.connect()
            logger.info(f"Подключен к каналу {channel.name}")
            return True
        except Exception as e:
            logger.error(f"Ошибка подключения к голосовому каналу: {e}", exc_info=True)
            return False

    async def disconnect(self):
        """Отключение от голосового канала."""
        if self.is_connected:
            await self.voice_client.disconnect()
            logger.info(f"Отключен от голосового канала на сервере {self.guild_id}")

        if self._disconnect_task:
            self._disconnect_task.cancel()
            self._disconnect_task = None

        self._voice_channel = None

    def add_to_queue(self, tracks: list[dict]):
        """
        Добавление треков в очередь.

        Args:
            tracks: Список треков для добавления
        """
        self.queue.extend(tracks)
        logger.info(f"Добавлено {len(tracks)} треков в очередь. Всего в очереди: {len(self.queue)}")

    async def play_next(self) -> bool:
        """
        Воспроизведение следующего трека в очереди.

        Returns:
            True если трек начал воспроизводиться, False если очередь пуста
        """
        async with self._play_lock:
            if self.current_index + 1 >= len(self.queue):
                logger.info("Достигнут конец очереди")
                return False

            self.current_index += 1
            return await self._play_track(self.queue[self.current_index])

    async def play_previous(self) -> bool:
        """
        Воспроизведение предыдущего трека в очереди.

        Returns:
            True если трек начал воспроизводиться, False если это первый трек
        """
        async with self._play_lock:
            if self.current_index <= 0:
                logger.info("Это первый трек в очереди")
                return False

            self.current_index -= 1
            return await self._play_track(self.queue[self.current_index])

    async def play_from_start(self) -> bool:
        """
        Начать воспроизведение с первого трека в очереди.

        Returns:
            True если воспроизведение началось, False если очередь пуста
        """
        async with self._play_lock:
            if not self.queue:
                logger.warning("Очередь пуста")
                return False

            self.current_index = 0
            return await self._play_track(self.queue[0])

    async def _play_track(self, track: dict) -> bool:
        """
        Внутренний метод для воспроизведения конкретного трека.

        Args:
            track: Информация о треке

        Returns:
            True если воспроизведение началось успешно
        """
        guild = self.bot.get_guild(self.guild_id)
        if not guild:
            logger.error("Гильдия не найдена")
            return False

        voice_client = guild.voice_client
        if not voice_client or not voice_client.is_connected():
            logger.error("Не подключен к голосовому каналу (voice_client отсутствует или не подключен)")
            return False

        try:
            if voice_client.is_playing() or voice_client.is_paused():
                self._manual_skip = True
                voice_client.stop()
                await asyncio.sleep(0.1)

            logger.info(f"Загрузка трека: {track['title']}")
            audio_source = await music_service.get_audio_source(track["url"])

            if not audio_source:
                logger.warning(f"Не удалось получить аудио-источник для {track['title']}, пропускаем трек")

                if self.text_channel:
                    try:
                        await self.text_channel.send(f"⚠️ Трек **{track['title']}** недоступен и был пропущен.")
                    except Exception as e:
                        logger.error(f"Ошибка отправки уведомления: {e}")

                if self.current_index + 1 < len(self.queue):
                    logger.info("Автоматический переход к следующему доступному треку")
                    self.current_index += 1
                    return await self._play_track(self.queue[self.current_index])
                else:
                    logger.warning("Больше нет доступных треков в очереди")
                    self.is_playing = False
                    return False

            self.current_track = track
            self.is_playing = True
            self.is_paused = False
            self.start_time = time.time()
            self.pause_time = None
            self.paused_duration = 0.0

            def after_playing(error):
                """Callback после завершения воспроизведения."""
                if error:
                    logger.error(f"Ошибка воспроизведения: {error}")

                asyncio.run_coroutine_threadsafe(self._auto_play_next(), voice_client.loop)

            voice_client.play(audio_source, after=after_playing)
            logger.info(f"Воспроизведение начато: {track['title']}")
            await self._update_player_ui()
            
            return True

        except Exception as e:
            logger.error(f"Ошибка при воспроизведении трека '{track['title']}': {e}", exc_info=True)

            if self.text_channel:
                try:
                    await self.text_channel.send(f"⚠️ Ошибка воспроизведения трека **{track['title']}**. Переход к следующему треку.")
                except Exception as notify_error:
                    logger.error(f"Ошибка отправки уведомления: {notify_error}")

            if self.current_index + 1 < len(self.queue):
                logger.info("Попытка воспроизвести следующий трек после ошибки")
                self.current_index += 1
                return await self._play_track(self.queue[self.current_index])
            else:
                logger.warning("Больше нет доступных треков в очереди")
                self.is_playing = False
                return False

    async def _auto_play_next(self):
        """Автоматическое воспроизведение следующего трека после завершения текущего."""
        self.is_playing = False

        if self._manual_skip:
            self._manual_skip = False
            return

        if self.current_index + 1 < len(self.queue):
            logger.info("Автоматическое переключение на следующий трек")
            await self.play_next()
        else:
            logger.info("Очередь завершена")
            self.current_track = None
            await self._schedule_disconnect()

    def pause(self) -> bool:
        """
        Пауза воспроизведения.

        Returns:
            True если пауза установлена успешно
        """
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.pause()
            self.is_paused = True
            self.pause_time = time.time()
            logger.info("Воспроизведение приостановлено")
            asyncio.create_task(self._schedule_disconnect())
            return True
        return False

    def resume(self) -> bool:
        """
        Возобновление воспроизведения.

        Returns:
            True если воспроизведение возобновлено успешно
        """
        if self.voice_client and self.voice_client.is_paused():
            self.voice_client.resume()
            self.is_paused = False
            self.is_playing = True

            if self.pause_time:
                self.paused_duration += time.time() - self.pause_time
                self.pause_time = None
            
            logger.info("Воспроизведение возобновлено")
            asyncio.create_task(self._schedule_disconnect())
            return True
        return False

    async def stop(self):
        """Остановка воспроизведения и очистка очереди."""
        if self.voice_client and (self.voice_client.is_playing() or self.voice_client.is_paused()):
            self.voice_client.stop()

        self.queue.clear()
        self.current_track = None
        self.current_index = -1
        self.is_playing = False
        self.is_paused = False

        logger.info("Воспроизведение остановлено, очередь очищена")
        await self._schedule_disconnect()

    def get_playback_position(self) -> tuple[int, int]:
        """
        Получение текущей позиции воспроизведения.
        
        Returns:
            Кортеж (текущая_позиция_сек, общая_длительность_сек)
        """
        if not self.current_track or not self.start_time:
            return (0, 0)
        
        duration = self.current_track.get("duration", 0)
        
        if self.is_paused and self.pause_time:
            elapsed = self.pause_time - self.start_time - self.paused_duration
        else:
            elapsed = time.time() - self.start_time - self.paused_duration

        position = min(int(elapsed), duration)
        return (position, duration)

    def get_queue_info(self) -> dict:
        """
        Получение информации об очереди.

        Returns:
            Словарь с информацией об очереди:
            - total: Общее количество треков
            - current_index: Индекс текущего трека
            - current_track: Информация о текущем треке
            - tracks: Список всех треков в очереди
        """
        return {
            "total": len(self.queue),
            "current_index": self.current_index,
            "current_track": self.current_track,
            "tracks": self.queue,
            "is_playing": self.is_playing,
            "is_paused": self.is_paused,
        }

    def set_text_channel(self, channel):
        """Установить текстовый канал для отправки сообщений проигрывателя."""
        self.text_channel = channel

    async def _update_player_ui(self):
        """Обновление или создание UI проигрывателя."""
        if not self.text_channel or not self.current_track:
            return

        if self.player_view and self.player_message:
            await self.player_view._update_player_message()
        else:
            pass

    async def clear_player_ui(self):
        """Очистка UI проигрывателя."""
        if self.player_message:
            try:
                await self.player_message.edit(
                    content="⏹️ Воспроизведение остановлено.",
                    embed=None,
                    view=None
                )
            except Exception as e:
                logger.error(f"Ошибка при очистке UI проигрывателя: {e}")
            
            self.player_message = None
            self.player_view = None
