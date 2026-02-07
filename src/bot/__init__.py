"""
Пакет для ботов.

Этот пакет содержит реализации ботов для различных платформ:
- Telegram бот (src.bot.telegram)
- Discord бот (src.bot.discord)
"""

# Ленивый импорт для избежания циклических зависимостей
def __getattr__(name):
    """Ленивый импорт компонентов."""
    if name in ("router", "LoggingMiddleware", "WhitelistMiddleware"):
        from src.bot.telegram import router, LoggingMiddleware, WhitelistMiddleware
        if name == "router":
            return router
        elif name == "LoggingMiddleware":
            return LoggingMiddleware
        elif name == "WhitelistMiddleware":
            return WhitelistMiddleware
    elif name in ("DiscordBot", "discord_bot"):
        from src.bot.discord import DiscordBot, discord_bot
        if name == "DiscordBot":
            return DiscordBot
        elif name == "discord_bot":
            return discord_bot
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Telegram
    "router",
    "LoggingMiddleware",
    "WhitelistMiddleware",
    # Discord
    "DiscordBot",
    "discord_bot",
]
