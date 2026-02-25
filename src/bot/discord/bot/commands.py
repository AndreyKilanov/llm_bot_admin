"""Модуль обработки команд Discord бота.

Содержит логику для музыкального плеера, управления очередью и информационных команд.
"""

import discord
from discord.ext import commands
from typing import Optional

from src.bot.discord.player import MusicPlayer, PlayerFactory
from src.bot.discord.views import MusicPlayerView, TrackSelectionView, QueuePaginationView
from src.services import music_service, SettingsService
from .constants import (
    ICON_SEARCH, ICON_MUSIC, ICON_SKIP, ICON_PREV, 
    ICON_PAUSE, ICON_RESUME, ICON_STOP, ICON_QUEUE,
    ICON_ROBOT, ICON_SPARKLE, ICON_INFO, ICON_ERR, ICON_OK,
    MSG_BOT_DISABLED, MSG_MUSIC_DISABLED, MSG_VOICE_REQUIRED,
    MSG_SEARCH_FAIL, MSG_CONN_FAIL, MSG_LOAD_FAIL, MSG_INVALID_URL,
    MSG_NOTHING_PLAYING, MSG_PLAYER_MISSING, MSG_QUEUE_EMPTY,
    MAX_SEARCH_RESULTS
)

class CommandHandlers:
    """Класс, содержащий логику обработки команд Discord бота.

    Предоставляет статические и классовые методы для управления музыкальным плеером,
    проверки прав доступа и отправки интерфейса управления.
    """

    @staticmethod
    def get_player(bot: commands.Bot, guild_id: int) -> MusicPlayer:
        """Возвращает экземпляр музыкального плеера для конкретного сервера.

        Args:
            bot: Экземпляр бота Discord.
            guild_id: ID сервера (гильдии), для которого нужен плеер.

        Returns:
            Экземпляр MusicPlayer.
        """
        return PlayerFactory.get_player(guild_id, bot)

    @staticmethod
    async def verify_ready(ctx: commands.Context) -> Optional[discord.VoiceChannel]:
        """Проверяет готовность бота и пользователя к воспроизведению.

        Проверяет, включен ли бот, разрешена ли музыка и находится ли автор
        команды в голосовом канале.

        Args:
            ctx: Контекст команды Discord.

        Returns:
            Голосовой канал автора, если все проверки пройдены, иначе None.
        """
        if not await SettingsService.is_discord_bot_enabled():
            await ctx.send(MSG_BOT_DISABLED)
            return None

        if not await SettingsService.is_discord_music_enabled():
            await ctx.send(MSG_MUSIC_DISABLED)
            return None

        if not ctx.author.voice:
            await ctx.send(MSG_VOICE_REQUIRED)
            return None

        return ctx.author.voice.channel

    @classmethod
    async def start_playback_sequence(cls, bot: commands.Bot, ctx: commands.Context, tracks: list, channel: discord.VoiceChannel) -> None:
        """Инициализирует последовательность воспроизведения треков.

        Подключается к каналу, добавляет треки в очередь и запускает проигрывание,
        если оно еще не активно. Также отправляет UI управления.

        Args:
            bot: Экземпляр бота Discord.
            ctx: Контекст команды Discord.
            tracks: Список метаданных треков для добавления.
            channel: Голосовой канал для подключения.
        """
        player = cls.get_player(bot, ctx.guild.id)
        player.set_text_channel(ctx.channel)

        if not await player.connect(channel):
            await ctx.send(MSG_CONN_FAIL)
            return

        player.add_to_queue(tracks)

        if not player.is_playing:
            await player.play_from_start()

        await cls.send_player_ui(ctx, player)

    @staticmethod
    async def send_player_ui(ctx: commands.Context, player: MusicPlayer) -> None:
        """Отправляет сообщение с интерфейсом управления плеером.

        Создает эмбед и кнопки управления, а также запускает автоматическое
        обновление статуса плеера.

        Args:
            ctx: Контекст команды Discord.
            player: Экземпляр музыкального плеера.
        """
        if not player.current_track:
            return

        view = MusicPlayerView(player, ctx)
        embed = view.create_player_embed()
        message = await ctx.send(embed=embed, view=view)
        
        player.player_view = view
        player.player_message = message
        view.message = message
        
        await view.start_auto_update()

    @classmethod
    async def handle_playmusic(cls, bot: commands.Bot, ctx: commands.Context, query: str) -> None:
        """Обрабатывает команду поиска и воспроизведения музыки.

        Выполняет поиск по запросу и либо сразу запускает воспроизведение (если найден один трек),
        либо предлагает пользователю выбрать трек из списка.

        Args:
            bot: Экземпляр бота Discord.
            ctx: Контекст команды Discord.
            query: Поисковый запрос.
        """
        v_channel = await cls.verify_ready(ctx)
        if not v_channel:
            return

        await ctx.send(f"{ICON_SEARCH} Поиск: **{query}**...")
        tracks = await music_service.search_tracks(query, max_results=MAX_SEARCH_RESULTS)

        if not tracks:
            await ctx.send(MSG_SEARCH_FAIL)
            return

        if len(tracks) == 1:
            await cls.start_playback_sequence(bot, ctx, tracks, v_channel)
            return

        embed = discord.Embed(
            title=f"{ICON_MUSIC} Результаты поиска",
            description="Выберите подходящий трек из списка ниже:",
            color=discord.Color.blue()
        )

        for i, track in enumerate(tracks, 1):
            length = music_service.format_duration(track.get("duration") or 0)
            embed.add_field(
                name=f"{i}. {track['title'][:100]}",
                value=f"Канал: {track['uploader']} | {length}",
                inline=False
            )

        player = cls.get_player(bot, ctx.guild.id)
        view = TrackSelectionView(tracks, player, ctx)
        message = await ctx.send(embed=embed, view=view)
        view.message = message

    @classmethod
    async def handle_link(cls, bot: commands.Bot, ctx: commands.Context, url: str) -> None:
        """Обрабатывает команду воспроизведения по прямой ссылке.

        Проверяет валидность URL, получает информацию о треке и запускает воспроизведение.

        Args:
            bot: Экземпляр бота Discord.
            ctx: Контекст команды Discord.
            url: Прямая ссылка на трек (например, YouTube).
        """
        v_channel = await cls.verify_ready(ctx)
        if not v_channel:
            return
            
        if not music_service.is_valid_url(url):
            await ctx.send(MSG_INVALID_URL)
            return

        await ctx.send(f"{ICON_SEARCH} Загрузка: <{url}>...")
        info = await music_service.get_track_info(url)
        
        if not info:
            await ctx.send(MSG_LOAD_FAIL)
            return

        await cls.start_playback_sequence(bot, ctx, [info], v_channel)

    @classmethod
    async def handle_playlist(cls, bot: commands.Bot, ctx: commands.Context, url: str) -> None:
        """Обрабатывает команду добавления плейлиста по ссылке.

        Получает все треки из плейлиста YouTube и добавляет их в очередь.

        Args:
            bot: Экземпляр бота Discord.
            ctx: Контекст команды Discord.
            url: Ссылка на плейлист (YouTube).
        """
        v_channel = await cls.verify_ready(ctx)
        if not v_channel:
            return
            
        if not music_service.is_valid_url(url):
            await ctx.send(MSG_INVALID_URL)
            return

        await ctx.send(f"{ICON_SEARCH} Загрузка плейлиста: <{url}>...")
        tracks = await music_service.get_playlist_info(url)
        
        if not tracks:
            await ctx.send(f"{ICON_ERR} Не удалось загрузить плейлист.")
            return

        await ctx.send(f"{ICON_OK} Найдено {len(tracks)} треков. Добавляю в очередь...")
        await cls.start_playback_sequence(bot, ctx, tracks, v_channel)

    @classmethod
    async def handle_skip(cls, bot: commands.Bot, ctx: commands.Context) -> None:
        """Переключает воспроизведение на следующий трек в очереди.

        Args:
            bot: Экземпляр бота Discord.
            ctx: Контекст команды Discord.
        """
        if not await cls.verify_ready(ctx): return
        player = cls.get_player(bot, ctx.guild.id)
        if not player or not player.is_playing:
            await ctx.send(MSG_NOTHING_PLAYING)
            return
        if await player.play_next():
            await ctx.send(f"{ICON_SKIP} Следующий трек.")
        else:
            await ctx.send(f"{ICON_ERR} Очередь окончена.")

    @classmethod
    async def handle_previous(cls, bot: commands.Bot, ctx: commands.Context) -> None:
        """Возвращает воспроизведение к предыдущему треку в очереди.

        Args:
            bot: Экземпляр бота Discord.
            ctx: Контекст команды Discord.
        """
        if not await cls.verify_ready(ctx): return
        player = cls.get_player(bot, ctx.guild.id)
        if not player or not player.is_playing:
            await ctx.send(MSG_NOTHING_PLAYING)
            return
        if await player.play_previous():
            await ctx.send(f"{ICON_PREV} Предыдущий трек.")
        else:
            await ctx.send(f"{ICON_ERR} Это первый трек.")

    @classmethod
    async def handle_pause(cls, bot: commands.Bot, ctx: commands.Context) -> None:
        """Приостанавливает текущее воспроизведение.

        Args:
            bot: Экземпляр бота Discord.
            ctx: Контекст команды Discord.
        """
        if not await cls.verify_ready(ctx): return
        player = cls.get_player(bot, ctx.guild.id)
        if not player or not player.is_playing:
            await ctx.send(MSG_NOTHING_PLAYING)
            return
        if player.pause():
            await ctx.send(f"{ICON_PAUSE} Музыка на паузе.")
        else:
            await ctx.send(f"{ICON_ERR} Ошибка при попытке паузы.")

    @classmethod
    async def handle_resume(cls, bot: commands.Bot, ctx: commands.Context) -> None:
        """Возобновляет приостановленное воспроизведение.

        Args:
            bot: Экземпляр бота Discord.
            ctx: Контекст команды Discord.
        """
        if not await cls.verify_ready(ctx): return
        player = cls.get_player(bot, ctx.guild.id)
        if not player:
            await ctx.send(MSG_PLAYER_MISSING)
            return
        if player.resume():
            await ctx.send(f"{ICON_RESUME} Продолжаем воспроизведение.")
        else:
            await ctx.send(f"{ICON_ERR} Плеер был активен.")

    @classmethod
    async def handle_stop(cls, bot: commands.Bot, ctx: commands.Context) -> None:
        """Останавливает воспроизведение и отключает бота от голосового канала.

        Args:
            bot: Экземпляр бота Discord.
            ctx: Контекст команды Discord.
        """
        if not await cls.verify_ready(ctx): return
        player = cls.get_player(bot, ctx.guild.id)
        if not player:
            await ctx.send(MSG_PLAYER_MISSING)
            return
        await player.stop()
        await player.disconnect()
        PlayerFactory.remove_player(ctx.guild.id)
        await ctx.send(f"{ICON_STOP} Плеер остановлен.")

    @classmethod
    async def handle_queue(cls, bot: commands.Bot, ctx: commands.Context) -> None:
        """Отображает текущую очередь воспроизведения.

        Показывает очередь с поддержкой пагинации.

        Args:
            bot: Экземпляр бота Discord.
            ctx: Контекст команды Discord.
        """
        if not await cls.verify_ready(ctx): return
        player = cls.get_player(bot, ctx.guild.id)
        if not player or not player.queue:
            await ctx.send(MSG_QUEUE_EMPTY)
            return
            
        view = QueuePaginationView(player, ctx)
        embed = view.create_embed()
        message = await ctx.send(embed=embed, view=view)
        view.message = message

    @classmethod
    async def handle_nowplaying(cls, bot: commands.Bot, ctx: commands.Context) -> None:
        """Отображает информацию о текущем воспроизводимом треке.

        Args:
            bot: Экземпляр бота Discord.
            ctx: Контекст команды Discord.
        """
        if not await cls.verify_ready(ctx): return
        player = cls.get_player(bot, ctx.guild.id)
        if not player or not player.current_track:
            await ctx.send(MSG_NOTHING_PLAYING)
            return
        track = player.current_track
        dur = music_service.format_duration(track.get("duration") or 0)
        embed = discord.Embed(title=f"{ICON_MUSIC} Сейчас играет", description=f"**{track['title']}**", color=discord.Color.purple())
        embed.add_field(name="Автор", value=track['uploader'], inline=True)
        embed.add_field(name="Длительность", value=dur, inline=True)
        if track.get('thumbnail'): embed.set_thumbnail(url=track['thumbnail'])
        status = "Пауза" if player.is_paused else "Играет"
        status_icon = ICON_PAUSE if player.is_paused else ICON_RESUME
        embed.add_field(name="Статус", value=f"{status_icon} {status}", inline=False)
        embed.set_footer(text=f"Трек {player.current_index + 1} из {len(player.queue)}")
        await ctx.send(embed=embed)

    @staticmethod
    async def handle_help(ctx: commands.Context) -> None:
        """Отображает справочную информацию о возможностях бота.

        Args:
            ctx: Контекст команды Discord.
        """
        embed = discord.Embed(
            title=f"{ICON_ROBOT} LLM Bot — Справка",
            description=(
                f"Я — мультифункциональный бот с AI и музыкой! {ICON_SPARKLE}\n\n"
                "**🧠 Чат с ИИ**\n• Отвечаю в ЛС или по упоминанию `@Бот`.\n\n"
                "**🎵 Плеер**\n"
                "• `/playmusic` — поиск (до 100 результатов, пагинация)\n"
                "• `/link` — играть по ссылке YouTube\n"
                "• `/playlist` — загрузить плейлист целиком\n"
                "• `/queue` — список треков (с пагинацией)\n"
                "• `/stop` — остановка и выход\n\n"
                "**⚙️ Управление**\n• `/pause` / `/resume`\n• `/skip` / `/previous`"
            ),
            color=discord.Color.from_rgb(88, 101, 242)
        )
        repo_url = "https://github.com/AndreyKilanov/llm_bot_admin/tree/dev"
        embed.description += f"\n\n-# [{ICON_INFO} GitHub Repository]({repo_url})"
        await ctx.send(embed=embed)
