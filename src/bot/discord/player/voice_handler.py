from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Final


from discord import VoiceClient, VoiceChannel, Client
from src.bot.discord.views.constants import ui_config

logger = logging.getLogger("discord.music_player.voice")


class VoiceHandler:
    """Класс для управления голосовым подключением в Discord."""

    def __init__(self, guild_id: int, bot: Client) -> None:
        """Инициализация обработчика голоса.

        Args:
            guild_id: ID сервера.
            bot: Экземпляр бота.
        """
        self.guild_id = guild_id
        self.bot = bot
        self.manual_skip: bool = False
        self._voice_channel: VoiceChannel | None = None
        self._intentional_disconnect: bool = False
        self._is_connecting: bool = False

    @property
    def voice_client(self) -> VoiceClient | None:
        """Текущий VoiceClient для сервера."""
        guild = self.bot.get_guild(self.guild_id)
        return guild.voice_client if guild else None

    @property
    def is_connected(self) -> bool:
        """Подключен ли бот к голосовому каналу."""
        vc = self.voice_client
        return vc is not None and vc.is_connected()

    async def connect(self, channel: VoiceChannel) -> bool:
        """Подключиться к голосовому каналу.

        Реализует отказоустойчивое подключение, обрабатывая "фантомные" сессии
        после перезапуска бота и принудительно очищая состояние при сбоях.

        Args:
            channel: Канал для подключения.

        Returns:
            True, если успешно подключено.
        """
        self._voice_channel = channel
        guild = self.bot.get_guild(self.guild_id)
        if not guild:
            return False

        vc: VoiceClient | None = guild.voice_client

        if vc and vc.is_connected() and vc.channel and vc.channel.id == channel.id:
            return True

        needs_reset = False
        if vc and not vc.is_connected():
            needs_reset = True
            logger.warning("VoiceClient на сервере %d не в сети. Сброс...", self.guild_id)
        elif guild.me.voice and not vc:
            needs_reset = True
            logger.warning("Обнаружена фантомная сессия на сервере %d. Очистка...", self.guild_id)

        if needs_reset:
            try:
                if vc:
                    await vc.disconnect(force=True)
                else:
                    await guild.change_voice_state(channel=None)
                await asyncio.sleep(1.0)
            except Exception as e:
                logger.debug("Ошибка при сбросе состояния голоса (игнорируется): %s", e)

        if vc and vc.is_connected() and vc.channel and vc.channel.id != channel.id:
            try:
                logger.info("Перемещение на сервере %d: %s -> %s", self.guild_id, vc.channel.name, channel.name)
                await vc.move_to(channel)
                return True
            except Exception as e:
                logger.error("Ошибка перемещения на сервере %d: %s. Пробую переподключиться.", self.guild_id, e)
                try:
                    await vc.disconnect(force=True)
                    await asyncio.sleep(0.5)
                except Exception:
                    pass

        self._is_connecting = True
        try:
            logger.info("Подключение к голосовому каналу '%s' сервера %d...", channel.name, self.guild_id)
            await channel.connect(timeout=ui_config.voice_connect_timeout, reconnect=True)
            return True
        except Exception as e:
            logger.error("Ошибка подключения на сервере %d: %s", self.guild_id, e)
            current_vc = guild.voice_client
            if current_vc:
                try:
                    await current_vc.disconnect(force=True)
                except Exception:
                    pass
            return False
        finally:
            self._is_connecting = False

    async def disconnect(self) -> None:
        """Отключиться от голосового канала (штатное отключение)."""
        self._intentional_disconnect = True
        vc = self.voice_client
        if vc and vc.is_connected():
            await vc.disconnect()
            logger.info("Отключен от голосового канала сервера %d", self.guild_id)
        self._voice_channel = None

    def stop_vc(self) -> None:
        """Остановить воспроизведение в VoiceClient."""
        vc = self.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            self.manual_skip = True
            vc.stop()
            logger.debug("Воспроизведение VoiceClient остановлено принудительно")

    def is_alone(self) -> bool:
        """Проверить, остался ли бот один в голосовом канале.
        
        Returns:
            True, если в канале нет других пользователей (кроме ботов).
        """
        vc = self.voice_client
        if not vc or not vc.channel:
            return False
            
        human_members = [m for m in vc.channel.members if not m.bot]
        return len(human_members) == 0
