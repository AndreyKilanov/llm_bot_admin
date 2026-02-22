from typing import Final

# Инфраструктурные константы
OPUS_PATH: Final[str] = "/usr/lib/x86_64-linux-gnu/libopus.so.0"
DEFAULT_PREFIX: Final[str] = "/"
MAX_SEARCH_RESULTS: Final[int] = 100

# Визуальные элементы (эмодзи)
ICON_ERR: Final[str] = "❌"
ICON_OK: Final[str] = "✅"
ICON_SEARCH: Final[str] = "🔍"
ICON_MUSIC: Final[str] = "🎵"
ICON_SKIP: Final[str] = "⏭️"
ICON_PREV: Final[str] = "⏮️"
ICON_PAUSE: Final[str] = "⏸️"
ICON_RESUME: Final[str] = "▶️"
ICON_STOP: Final[str] = "⏹️"
ICON_QUEUE: Final[str] = "📋"
ICON_INFO: Final[str] = "ℹ️"
ICON_ROBOT: Final[str] = "🤖"
ICON_SPARKLE: Final[str] = "✨"

# Ответы пользователю
MSG_BOT_DISABLED: Final[str] = f"{ICON_ERR} Discord бот отключен в настройках администратора."
MSG_MUSIC_DISABLED: Final[str] = f"{ICON_ERR} Музыкальный плеер отключен в настройках администратора."
MSG_VOICE_REQUIRED: Final[str] = f"{ICON_ERR} Вы должны находиться в голосовом канале!"
MSG_SEARCH_FAIL: Final[str] = f"{ICON_ERR} Треки не найдены."
MSG_CONN_FAIL: Final[str] = f"{ICON_ERR} Не удалось подключиться к голосовому каналу."
MSG_LOAD_FAIL: Final[str] = f"{ICON_ERR} Не удалось получить информацию о треке."
MSG_INVALID_URL: Final[str] = f"{ICON_ERR} Некорректная ссылка на YouTube."
MSG_NOTHING_PLAYING: Final[str] = f"{ICON_ERR} Ничего не воспроизводится."
MSG_PLAYER_MISSING: Final[str] = f"{ICON_ERR} Плеер не найден."
MSG_QUEUE_EMPTY: Final[str] = f"{ICON_ERR} Очередь пуста."
