from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Final

import discord

if TYPE_CHECKING:
    from discord import VoiceClient, VoiceChannel, Client

logger = logging.getLogger("discord.music_player.voice")

CONNECT_TIMEOUT: Final[float] = 20.0


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

        Args:
            channel: Канал для подключения.

        Returns:
            True, если успешно.
        """
        self._voice_channel = channel
        guild = self.bot.get_guild(self.guild_id)
        if not guild:
            return False

        vc = guild.voice_client

        if vc and vc.channel and vc.channel.id == channel.id and vc.is_connected():
            return True

        if vc:
            try:
                if vc.channel and vc.channel.id != channel.id:
                    logger.info("Перемещение на сервере %d в канал %s", self.guild_id, channel.name)
                    await vc.move_to(channel)
                    return True
                
                if not vc.is_connected():
                    await vc.disconnect(force=True)
            except Exception as e:
                logger.error("Ошибка подготовки VoiceClient на сервере %d: %s", self.guild_id, e)
                try:
                    await vc.disconnect(force=True)
                except Exception:
                    pass

        try:
            await channel.connect(timeout=CONNECT_TIMEOUT, reconnect=True)
            logger.info("Подключен к каналу %s сервера %d", channel.name, self.guild_id)
            return True
        except Exception as e:
            logger.error("Ошибка подключения на сервере %d: %s", self.guild_id, e)
            return False

    async def disconnect(self) -> None:
        """Отключиться от голосового канала."""
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
