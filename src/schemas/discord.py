from typing import Union, Any
import discord
from pydantic import BaseModel, ConfigDict, Field


class BotCommand(BaseModel):
    """Схема для описания одной команды бота."""
    name: str
    description: str


class BotEmojis(BaseModel):
    """Схема для хранения всех эмодзи бота (кастомных или Unicode fallback)."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)

    shuffle: Union[discord.Emoji, str] = "🔀"
    norepeat: Union[discord.Emoji, str] = "↔️"
    repeat1: Union[discord.Emoji, str] = "🔂"
    repeat_all: Union[discord.Emoji, str] = "🔁"
    rewind: Union[discord.Emoji, str] = "⏮"
    previous: Union[discord.Emoji, str] = "⏮️"
    next: Union[discord.Emoji, str] = "⏭️"
    forward: Union[discord.Emoji, str] = "⏩"
    queue: Union[discord.Emoji, str] = "≡"
    lyrics: Union[discord.Emoji, str] = "🅐"
    stop_only: Union[discord.Emoji, str] = "⏹"
    play: Union[discord.Emoji, str] = "▶️"
    pause: Union[discord.Emoji, str] = "⏸️"
    mute: Union[discord.Emoji, str] = "🔇"
    unmute: Union[discord.Emoji, str] = "🔊"
    vol_down: Union[discord.Emoji, str] = "🔉"
    vol_up: Union[discord.Emoji, str] = "🔊"
    add_query: Union[discord.Emoji, str] = "➕"
    disconnect: Union[discord.Emoji, str] = "❌"
    
    # Статусные эмодзи
    success: str = "✅"
    error: str = "❌"
    timeout: str = "⏱️"
    sparkle: str = "✨"
    robot: str = "🤖"
    info: str = "ℹ️"
    search: str = "🔍"


class BotCommandsConfig(BaseModel):
    """Схема для всех имен и описаний команд бота."""
    
    play: BotCommand = BotCommand(name="play", description="Искать и играть музыку (YouTube)")
    link: BotCommand = BotCommand(name="link", description="Играть по прямой ссылке")
    playlist: BotCommand = BotCommand(name="playlist", description="Загрузить плейлист")
    skip: BotCommand = BotCommand(name="skip", description="К следующему треку")
    previous: BotCommand = BotCommand(name="previous", description="К предыдущему треку")
    pause: BotCommand = BotCommand(name="pause", description="Поставить на паузу")
    resume: BotCommand = BotCommand(name="resume", description="Продолжить музыку")
    stop: BotCommand = BotCommand(name="stop", description="Остановка и выход")
    help: BotCommand = BotCommand(name="help", description="Справка по боту")
    search: BotCommand = BotCommand(name="search", description="Живой поиск музыки в YouTube")
    queue: BotCommand = BotCommand(name="queue", description="Очередь треков")
    lyrics: BotCommand = BotCommand(name="lyrics", description="Показать текст текущей песни")
