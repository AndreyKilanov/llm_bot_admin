from typing import Final
import discord

# Константы для оформления
DEFAULT_EMBED_COLOR: Final[int] = 0x9B59B6
SUCCESS_COLOR: Final[discord.Color] = discord.Color.green()
ERROR_COLOR: Final[discord.Color] = discord.Color.red()
PROGRESS_BAR_LENGTH: Final[int] = 15
DEFAULT_VIEW_TIMEOUT: Final[float] = 60.0

# Эмодзи
EMOJI_PREVIOUS: Final[str] = "⏮️"
EMOJI_PLAY: Final[str] = "▶️"
EMOJI_PAUSE: Final[str] = "⏸️"
EMOJI_NEXT: Final[str] = "⏭️"
EMOJI_STOP: Final[str] = "⏹️"
EMOJI_REWIND: Final[str] = "⏪"
EMOJI_FORWARD: Final[str] = "⏩"
EMOJI_QUEUE: Final[str] = "📋"
EMOJI_LOOP_NONE: Final[str] = "🚫"
EMOJI_LOOP_TRACK: Final[str] = "🔂"
EMOJI_LOOP_PLAYLIST: Final[str] = "🔁"
EMOJI_SUCCESS: Final[str] = "✅"
EMOJI_ERROR: Final[str] = "❌"
EMOJI_TIMEOUT: Final[str] = "⏱️"
