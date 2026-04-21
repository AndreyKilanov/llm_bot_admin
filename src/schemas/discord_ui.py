from pydantic import BaseModel


class BotUIConfig(BaseModel):
    """Схема для всех текстовых сообщений и настроек оформления бота."""
    
    # Оформление
    embed_color: int = 0x9B59B6
    progress_bar_length: int = 20
    notification_timeout: float = 10.0
    max_search_results: int = 50
    default_view_timeout: float = 60.0
    items_per_page: int = 10
    invisible_spacer: str = "⠀" * 30
    
    # Общие сообщения
    msg_unknown: str = "Неизвестно"
    msg_error: str = "❌ Произошла ошибка."
    
    # Плеер
    msg_now_playing: str = "🎵 Сейчас играет"
    msg_progress: str = "Прогресс"
    msg_loop_mode: str = "Режим"
    msg_player_footer: str = "♫ Трек {current} из {total}"
    msg_player_empty: str = "Нет активного трека в данный момент."
    msg_playback_stopped: str = "⏹️ Воспроизведение остановлено. Бот остался в канале."
    
    # Режимы повтора
    msg_loop_off: str = "выключено"
    msg_loop_track: str = "трек"
    msg_loop_playlist: str = "плейлист"
    
    # Ошибки плеера
    msg_err_no_active_track: str = "❌ Нет активного трека."
    msg_err_queue_empty: str = "❌ Очередь пуста."
    msg_err_first_track: str = "❌ Это первый трек в очереди."
    msg_err_last_track: str = "❌ Это последний трек в очереди."
    msg_err_play_fail: str = "❌ Не удалось запустить воспроизведение."
    msg_no_lyrics: str = "❌ Текст песни не найден для этого трека."
    
    # Команды и права
    msg_bot_disabled: str = "❌ Discord бот отключен в настройках администратора."
    msg_music_disabled: str = "❌ Музыкальный плеер отключен в настройках администратора."
    msg_voice_required: str = "❌ Вы должны находиться в голосовом канале!"
    
    # Поиск и загрузка
    msg_search_results_title: str = "🔍 Результаты поиска"
    msg_search_results_desc: str = "Выберите подходящий трек из списка ниже:"
    msg_search_fail: str = "❌ Треки не найдены."
    msg_conn_fail: str = "❌ Не удалось подключиться к голосовому канале."
    msg_load_fail: str = "❌ Не удалось получить информацию о треке."
    msg_invalid_url: str = "❌ Некорректная ссылка на YouTube."
    msg_err_no_active_track_fallback: str = "Ничего не воспроизводится."
    msg_err_player_not_found: str = "Плеер не найден."
    msg_err_queue_empty_fallback: str = "Очередь пуста."

    # Сообщения чата и LLM
    msg_err_llm_internal: str = "❌ Произошла внутренняя ошибка при обращении к нейросети"
    msg_err_llm_connection: str = "❌ Отсутствует активное соединение с LLM API"
    msg_err_config_base: str = "❌ Ошибка конфигурации: {error_msg}"
    msg_err_play_fail_v2: str = "Не удалось запустить трек."
    msg_err_not_in_voice: str = "Вы больше не в голосовом канале!"
    msg_track_added: str = "✅ Трек добавлен в очередь!"
    msg_tracks_added: str = "✅ Добавлено {count} треков в очередь!"
    msg_selection_timeout: str = "⏱️ Время выбора истекло."
    msg_muted: str = "🔇 Заглушено."
    msg_unmuted: str = "🔊 Звук включён."
    msg_volume_set: str = "🔊 Громкость: {volume}%"
    msg_volume_max: str = "⚠️ Достигнут максимальный уровень громкости (100%)"
    msg_queue_empty_v2: str = "❌ Очередь пуста."

    # Модальные окна
    msg_search_modal_title: str = "Поиск музыки"
    msg_search_modal_label: str = "Запрос или ссылка (YouTube/VK)"
    msg_search_modal_placeholder: str = "Введите название трека или вставьте ссылку..."
    msg_cog_missing: str = "❌ Музыкальный модуль не найден."

    # Надписи на кнопках и плейсхолдеры
    label_add_all: str = "Добавить все"
    label_prev_page: str = "◀ Назад"
    label_next_page: str = "Вперед ▶"
    placeholder_select_track: str = "Выберите трек из списка..."
    placeholder_queue_select: str = "Выберите трек для воспроизведения..."
    
    # Стили кнопок (discord.ButtonStyle значения)
    style_primary: int = 1    # Blurple
    style_secondary: int = 2  # Grey
    style_success: int = 3    # Green
    style_danger: int = 4     # Red
    
    # Специфические настройки для кнопок плеера
    msg_shuffle_on: str = "🔀 Очередь перемешана!"
    msg_err_too_many_errors: str = "❌ Слишком много ошибок в очереди. Воспроизведение остановлено."
    msg_err_track_unavailable: str = "⚠️ Трек **{title}** недоступен (приватный или удален). Пропускаю..."
    msg_err_load_track: str = "⚠️ Ошибка при загрузке трека **{title}**."

    # Технические параметры (задержки и таймауты)
    opus_path: str = "/usr/lib/x86_64-linux-gnu/libopus.so.0"
    default_prefix: str = "/"
    player_disconnect_delay: int = 600  # 10 минут простоя
    playlist_clear_timeout: int = 1800  # 30 минут хранения очереди
    ui_update_delay: float = 0.1       # Задержка перед обновлением UI
    voice_connect_timeout: float = 20.0 # Таймаут подключения к каналу
    notification_delete_delay: float = 10.0 # Время удаления уведомлений об ошибках
    
    # Параметры текстового чата
    max_message_length: int = 2000
    default_memory_limit: int = 10
    setting_allow_new_chats: str = "discord_allow_new_chats"
    setting_allow_dms: str = "discord_allow_dms"
    setting_memory_limit: str = "discord_memory_limit"
    
    # Пагинация и списки
    items_per_page: int = 10
    msg_queue_title: str = "Список треков"
    msg_queue_desc: str = "Всего в очереди: **{total}**"

    # Параметры автодополнения (живой поиск)
    autocomplete_max_results: int = 10
    autocomplete_loop_limit: int = 9
    autocomplete_search_prefix: str = "🔍 Искать: {query}"
    autocomplete_title_limit: int = 80
    autocomplete_uploader_limit: int = 15
    autocomplete_choice_limit: int = 100
    autocomplete_separator: str = " | "
