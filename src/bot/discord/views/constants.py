from typing import Final
import discord

# Константы для оформления
DEFAULT_EMBED_COLOR: Final[int] = 0x9B59B6
SUCCESS_COLOR: Final[discord.Color] = discord.Color.green()
ERROR_COLOR: Final[discord.Color] = discord.Color.red()
SEARCH_COLOR: Final[discord.Color] = discord.Color.blue()
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
EMOJI_SEARCH: Final[str] = "🎵"
EMOJI_LOOP_NONE: Final[str] = "🚫"
EMOJI_LOOP_TRACK: Final[str] = "🔂"
EMOJI_LOOP_PLAYLIST: Final[str] = "🔁"
EMOJI_SUCCESS: Final[str] = "✅"
EMOJI_ERROR: Final[str] = "❌"
EMOJI_TIMEOUT: Final[str] = "⏱️"
EMOJI_PREV_PAGE: Final[str] = "◀"
EMOJI_NEXT_PAGE: Final[str] = "▶"

# Настройки пагинации
DEFAULT_ITEMS_PER_PAGE: Final[int] = 5
LABEL_PREV_PAGE: Final[str] = f"{EMOJI_PREV_PAGE} Назад"
LABEL_NEXT_PAGE: Final[str] = f"Вперед {EMOJI_NEXT_PAGE}"
LABEL_ADD_ALL: Final[str] = "Добавить все"

# Сообщения пользователю
MSG_SEARCH_RESULTS_TITLE: Final[str] = f"{EMOJI_SEARCH} Результаты поиска"
MSG_SEARCH_RESULTS_DESC: Final[str] = "Выберите подходящий трек из списка ниже:"
MSG_UNKNOWN: Final[str] = "Неизвестно"
MSG_TRACK_ADDED: Final[str] = f"{EMOJI_SUCCESS} Трек добавлен в очередь!"
MSG_TRACKS_ADDED: Final[str] = f"{EMOJI_SUCCESS} Добавлено {{count}} треков в очередь!"
MSG_SELECTION_TIMEOUT: Final[str] = f"{EMOJI_TIMEOUT} Время выбора истекло."
MSG_SEARCH_FOOTER: Final[str] = "Найдено: {total} | Страница {current} из {pages}"
MSG_UPLOADER_INFO: Final[str] = "Канал: {uploader} | {duration}"

# Очередь
MSG_QUEUE_TITLE: Final[str] = f"{EMOJI_QUEUE} Список треков"
MSG_QUEUE_TOTAL: Final[str] = "Всего в очереди: **{total}**"
MSG_QUEUE_EMPTY: Final[str] = "Очередь пуста."
MSG_QUEUE_FOOTER: Final[str] = "Страница {current} из {pages}"
MSG_TRACK_INFO: Final[str] = "{uploader} | {duration}"

# Плеер
MSG_PLAYER_TITLE: Final[str] = "🎵 Проигрыватель"
MSG_PLAYER_EMPTY: Final[str] = "Нет активного трека в данный момент."
MSG_NOW_PLAYING: Final[str] = "🎵 Сейчас играет"
MSG_DURATION: Final[str] = "Длительность"
MSG_STATUS: Final[str] = "Статус"
MSG_PROGRESS: Final[str] = "Прогресс"
MSG_LOOP_MODE: Final[str] = "Режим"
MSG_STOPPED: Final[str] = f"{EMOJI_STOP} Воспроизведение остановлено."

MSG_STATUS_PAUSED: Final[str] = f"{EMOJI_PAUSE} На паузе"
MSG_STATUS_PLAYING: Final[str] = f"{EMOJI_PLAY} Воспроизводится"
MSG_STATUS_FINISHED: Final[str] = "🏁 Завершено"

MSG_ERR_FIRST_TRACK: Final[str] = f"{EMOJI_ERROR} Это первый трек в очереди."
MSG_ERR_LAST_TRACK: Final[str] = f"{EMOJI_ERROR} Это последний трек в очереди."
MSG_ERR_NO_ACTIVE_TRACK: Final[str] = f"{EMOJI_ERROR} Нет активного трека."
MSG_ERR_PLAY_FAIL: Final[str] = f"{EMOJI_ERROR} Не удалось запустить воспроизведение."
MSG_ERR_RESUME_FAIL: Final[str] = "Не удалось возобновить воспроизведение."
MSG_ERR_PAUSE_FAIL: Final[str] = "Не удалось приостановить воспроизведение."
MSG_ERR_SEEK_FAIL: Final[str] = f"{EMOJI_ERROR} Не удалось перемотать {{direction}} на {{seconds}}с."
MSG_ERR_QUEUE_EMPTY: Final[str] = f"{EMOJI_ERROR} Очередь пуста."

MSG_LOOP_CHANGED: Final[str] = "🔄 Режим зацикливания: **{mode}**."
MSG_LOOP_OFF: Final[str] = "выключено"
MSG_LOOP_TRACK: Final[str] = "трек"
MSG_LOOP_PLAYLIST: Final[str] = "плейлист"
MSG_LOOP_UNKNOWN: Final[str] = "неизвестно"

MSG_QUEUE_EXTENDED: Final[str] = "... и еще {count} треков"
MSG_PLAYER_FOOTER: Final[str] = "♫ Трек {current} из {total}"
