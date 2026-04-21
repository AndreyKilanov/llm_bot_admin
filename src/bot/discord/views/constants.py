from typing import Final
import discord
from src.schemas import BotUIConfig, BotCommandsConfig

# Технические константы оформления
UI_WIDTH: Final[int] = 30

# Лимиты
MAX_SEARCH_RESULTS: Final[int] = 50

# Источники треков (для footer embed)
SOURCE_LABELS: Final[dict[str, str]] = {
    "youtube": "YouTube",
    "vk": "ВКонтакте",
    "unknown": "Источник",
}
SOURCE_ICON_URLS: Final[dict[str, str]] = {
    "youtube": "https://www.youtube.com/favicon.ico",
    "vk": "https://vk.com/images/icons/favicons/fav_logo.ico",
    "unknown": "",
}

# Глобальный конфиг UI (все значения по умолчанию берутся из BotUIConfig)
ui_config = BotUIConfig()
commands_config = BotCommandsConfig()

