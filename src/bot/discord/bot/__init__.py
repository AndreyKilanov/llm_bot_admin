from .client import DiscordBot

# Экспорт основного класса и создание глобального инстанса
discord_bot = DiscordBot()

__all__ = ["DiscordBot", "discord_bot"]
