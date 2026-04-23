"""Инициализация Discord модуля.

Экспортирует основной класс бота и глобальный экземпляр.
"""

from .client import DiscordBot

discord_bot = DiscordBot()

__all__ = ["DiscordBot", "discord_bot"]
