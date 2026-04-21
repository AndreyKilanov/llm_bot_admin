"""Инициализация расширения команд Discord бота.

Регистрирует все логические коги при загрузке.
"""

from discord.ext import commands

from .playback import PlaybackCommands
from .control import ControlCommands
from .info import InfoCommands


async def setup(bot: commands.Bot) -> None:
    """Точка входа для загрузки всех когов музыкальных команд.

    Args:
        bot: Экземпляр бота discord.py.
    """
    await bot.add_cog(PlaybackCommands(bot))
    await bot.add_cog(ControlCommands(bot))
    await bot.add_cog(InfoCommands(bot))
