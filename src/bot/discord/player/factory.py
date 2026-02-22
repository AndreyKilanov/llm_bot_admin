from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .player import MusicPlayer

if TYPE_CHECKING:
    from discord import Client

logger = logging.getLogger("discord.music_player.factory")


class PlayerFactory:
    """Фабрика для управления экземплярами MusicPlayer для разных серверов."""

    _instances: dict[int, MusicPlayer] = {}

    @classmethod
    def get_player(cls, guild_id: int, bot: Client) -> MusicPlayer:
        """Получить или создать музыкальный плеер для гильдии.

        Args:
            guild_id: ID сервера Discord.
            bot: Экземпляр бота.

        Returns:
            Экземпляр MusicPlayer.
        """
        if guild_id not in cls._instances:
            logger.info("Создание нового MusicPlayer для гильдии %d", guild_id)
            cls._instances[guild_id] = MusicPlayer(guild_id, bot)
        
        return cls._instances[guild_id]

    @classmethod
    def remove_player(cls, guild_id: int) -> None:
        """Удалить плеер гильдии из реестра.

        Args:
            guild_id: ID сервера Discord.
        """
        if guild_id in cls._instances:
            logger.info("Удаление MusicPlayer гильдии %d из реестра", guild_id)
            del cls._instances[guild_id]
            
    @classmethod
    def get_all_players(cls) -> dict[int, MusicPlayer]:
        """Получить все активные плееры.

        Returns:
            Словарь {guild_id: MusicPlayer}.
        """
        return cls._instances
