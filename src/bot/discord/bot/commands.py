"""Модуль обработки команд Discord бота.

Содержит логику для музыкального плеера, управления очередью и информационных команд.
"""

import asyncio
import discord
from discord.ext import commands
from typing import Optional, Union

from src.bot.discord.player import MusicPlayer, PlayerFactory
from src.bot.discord.views import MusicPlayerView, TrackSelectionView, QueuePaginationView
from src.services import music_service, SettingsService
from .constants import (
    ICON_SEARCH, ICON_MUSIC, ICON_SKIP, ICON_PREV, 
    ICON_PAUSE, ICON_RESUME, ICON_STOP, ICON_QUEUE,
    ICON_ROBOT, ICON_SPARKLE, ICON_INFO, ICON_ERR, ICON_OK,
    MSG_BOT_DISABLED, MSG_MUSIC_DISABLED, MSG_VOICE_REQUIRED,
    MSG_SEARCH_FAIL, MSG_CONN_FAIL, MSG_LOAD_FAIL, MSG_INVALID_URL,
    MSG_NOTHING_PLAYING, MSG_PLAYER_MISSING, MSG_QUEUE_EMPTY
)
from src.bot.discord.views.constants import MAX_SEARCH_RESULTS, NOTIFICATION_TIMEOUT
from src.logger import get_logger

logger = get_logger(__name__)

class CommandHandlers:
    """Класс, содержащий логику обработки команд Discord бота.

    Предоставляет статические и классовые методы для управления музыкальным плеером,
    проверки прав доступа и отправки интерфейса управления.
    """

    @staticmethod
    async def _delete_with_delay(message: Union[discord.Message, discord.WebhookMessage], delay: float) -> None:
        """Безопасно удаляет сообщение через указанную задержку.

        Args:
            message: Сообщение или WebhookMessage для удаления.
            delay: Задержка в секундах.
        """
        try:
            await message.delete(delay=delay)
        except (TypeError, discord.HTTPException, discord.Forbidden):
            async def delayed_delete():
                await asyncio.sleep(delay)
                try:
                    await message.delete()
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    pass
            
            asyncio.create_task(delayed_delete())

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
            await ctx.send(MSG_BOT_DISABLED, delete_after=NOTIFICATION_TIMEOUT)
            return None

        if not await SettingsService.is_discord_music_enabled():
            await ctx.send(MSG_MUSIC_DISABLED, delete_after=NOTIFICATION_TIMEOUT)
            return None

        if not ctx.author.voice:
            await ctx.send(MSG_VOICE_REQUIRED, delete_after=NOTIFICATION_TIMEOUT)
            return None

        return ctx.author.voice.channel

    @classmethod
    async def start_playback_sequence(
        cls, 
        bot: commands.Bot, 
        ctx: Union[commands.Context, discord.Interaction], 
        tracks: list, 
        channel: discord.VoiceChannel
    ) -> None:
        """Инициализирует последовательность воспроизведения треков.

        Подключается к каналу, добавляет треки в очередь и запускает проигрывание,
        если оно еще не активно. Также отправляет UI управления.

        Args:
            bot: Экземпляр бота Discord.
            ctx: Контекст команды или Interaction.
            tracks: Список метаданных треков для добавления.
            channel: Голосовой канал для подключения.
        """
        guild_id = ctx.guild.id if isinstance(ctx, commands.Context) else ctx.guild_id
        text_channel = ctx.channel
        user = ctx.author if isinstance(ctx, commands.Context) else ctx.user
        author_name = user.display_name

        player = cls.get_player(bot, guild_id)
        player.set_text_channel(text_channel)

        if not await player.connect(channel):
            if isinstance(ctx, commands.Context):
                await ctx.send(MSG_CONN_FAIL, delete_after=NOTIFICATION_TIMEOUT)
            else:
                await ctx.response.send_message(MSG_CONN_FAIL, ephemeral=True)
            return

        for track in tracks:
            track.setdefault("added_by", author_name)
            track.setdefault("source", cls._detect_source(str(track.get("url", ""))))

        player.add_to_queue(tracks)

        if not player.is_playing:
            await player.play_from_start()

        await cls.send_player_ui(ctx, player)

    @staticmethod
    def _detect_source(url: str) -> str:
        """Определить источник трека по URL.

        Args:
            url: URL трека.

        Returns:
            Строка-идентификатор: 'youtube', 'vk' или 'unknown'.
        """
        if "youtube.com" in url or "youtu.be" in url:
            return "youtube"
        if "vk.com" in url or "vk.ru" in url:
            return "vk"
        return "unknown"


    @staticmethod
    async def send_player_ui(ctx: Union[commands.Context, discord.Interaction], player: MusicPlayer) -> None:
        """Отправляет сообщение с интерфейсом управления плеером.

        Args:
            ctx: Контекст команды или Interaction.
            player: Экземпляр музыкального плеера.
        """
        if not player.current_track:
            return

        if player.player_message:
            await player.clear_player_ui()

        view = MusicPlayerView(player, ctx)
        embed = view.create_player_embed()
        
        if isinstance(ctx, commands.Context):
            message = await ctx.send(embed=embed, view=view)
        else:
            if ctx.response.is_done():
                message = await ctx.followup.send(embed=embed, view=view)
            else:
                await ctx.response.send_message(embed=embed, view=view)
                message = await ctx.original_response()
        
        player.player_view = view
        player.player_message = message
        view.message = message
        
        await view.start_auto_update()

    @classmethod
    async def handle_search(cls, bot: commands.Bot, interaction: discord.Interaction, query: str) -> None:
        """Обрабатывает поиск после того как defer() уже отправлен.

        Этот метод вызывается только из search_slash, где defer() уже выполнен.
        Использует исключительно interaction.followup для всех ответов.

        Args:
            bot: Экземпляр бота.
            interaction: Объект взаимодействия (defer уже отправлен).
            query: Поисковый запрос или URL.
        """
        if not await SettingsService.is_discord_bot_enabled():
            await interaction.followup.send(MSG_BOT_DISABLED, ephemeral=True)
            return

        if not await SettingsService.is_discord_music_enabled():
            await interaction.followup.send(MSG_MUSIC_DISABLED, ephemeral=True)
            return

        if not interaction.user.voice:
            try:
                await interaction.followup.send(MSG_VOICE_REQUIRED, ephemeral=True)
            except discord.HTTPException:
                pass
            return

        v_channel = interaction.user.voice.channel

        try:
            if music_service.is_valid_url(query):
                try:
                    info = await asyncio.wait_for(music_service.get_track_info(query), timeout=30.0)
                except asyncio.TimeoutError:
                    await interaction.followup.send("⚠️ Время ожидания поиска истекло. Пожалуйста, повторите попытку позже.", ephemeral=True)
                    return
                
                if not info:
                    await interaction.followup.send(MSG_LOAD_FAIL, ephemeral=True)
                    return

                await interaction.followup.send(f"{ICON_OK} Добавлено: **{info['title']}**", ephemeral=True)
                await cls.start_playback_sequence(bot, interaction, [info], v_channel)
                return

            try:
                tracks = await asyncio.wait_for(music_service.search_tracks(query, max_results=MAX_SEARCH_RESULTS), timeout=30.0)
            except asyncio.TimeoutError:
                await interaction.followup.send("⚠️ Время ожидания поиска истекло. Пожалуйста, повторите попытку позже.", ephemeral=True)
                return

            if not tracks:
                await interaction.followup.send(MSG_SEARCH_FAIL, ephemeral=True)
                return

            if len(tracks) == 1:
                await interaction.followup.send(f"{ICON_OK} Добавлено: **{tracks[0]['title']}**", ephemeral=True)
                await cls.start_playback_sequence(bot, interaction, tracks, v_channel)
            else:
                player = cls.get_player(bot, interaction.guild_id)
                view = TrackSelectionView(tracks, player, interaction)
                embed = view.create_embed()
                msg = await interaction.followup.send(embed=embed, view=view)
                view.message = msg

        except (discord.NotFound, discord.HTTPException) as exc:
            if isinstance(exc, discord.NotFound) and exc.code in (10062, 10015):
                logger.debug("handle_search: токен взаимодействия истёк или не найден: %s", exc)
            else:
                logger.error("handle_search: ошибка при отправке followup: %s", exc)

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

        status_msg = await ctx.send(f"{ICON_SEARCH} Поиск: **{query}**...")
        tracks = await music_service.search_tracks(query, max_results=MAX_SEARCH_RESULTS)

        if not tracks:
            await status_msg.edit(content=MSG_SEARCH_FAIL)
            await cls._delete_with_delay(status_msg, NOTIFICATION_TIMEOUT)
            return

        if len(tracks) == 1:
            track = tracks[0]
            await status_msg.edit(content=f"{ICON_OK} Трек найден и добавлен: **{track['title']}**")
            await cls.start_playback_sequence(bot, ctx, tracks, v_channel)
            return

        player = cls.get_player(bot, ctx.guild.id)
        view = TrackSelectionView(tracks, player, ctx)
        embed = view.create_embed()
        await status_msg.edit(content=None, embed=embed, view=view)
        view.message = status_msg

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
            await ctx.send(MSG_INVALID_URL, delete_after=NOTIFICATION_TIMEOUT)
            return

        status_msg = await ctx.send(f"{ICON_SEARCH} Загрузка: <{url}>...")
        info = await music_service.get_track_info(url)
        
        if not info:
            await status_msg.edit(content=MSG_LOAD_FAIL)
            return

        await status_msg.edit(content=f"{ICON_OK} Трек добавлен: **{info['title']}**")
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
            await ctx.send(MSG_INVALID_URL, delete_after=NOTIFICATION_TIMEOUT)
            return

        status_msg = await ctx.send(f"{ICON_SEARCH} Загрузка плейлиста: <{url}>...")
        tracks = await music_service.get_playlist_info(url)
        
        if not tracks:
            await status_msg.edit(content=f"{ICON_ERR} Не удалось загрузить плейлист.")
            return

        await status_msg.edit(content=f"{ICON_OK} Найдено {len(tracks)} треков. Добавляю в очередь...")
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
        await ctx.send(f"{ICON_STOP} Плеер остановлен.", delete_after=NOTIFICATION_TIMEOUT)

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
            
        await cls.send_player_ui(ctx, player)

    @staticmethod
    async def handle_help(ctx: commands.Context) -> None:
        """Отображает справочную информацию о возможностях бота.

        Args:
            ctx: Контекст команды Discord.
        """
        from src.bot.discord.views.emoji_manager import emoji_manager
        e_prev = emoji_manager.get("previous")
        e_play = emoji_manager.get("play")
        e_pause = emoji_manager.get("pause")
        e_next = emoji_manager.get("next")
        e_stop = emoji_manager.get("stop_only")
        e_queue = emoji_manager.get("queue")
        e_shuffle = emoji_manager.get("shuffle")
        e_loop = emoji_manager.get("repeat_all")

        embed = discord.Embed(
            title=f"{ICON_ROBOT} LLM Bot — Справка",
            description=(
                f"Я — мультифункциональный бот с ИИ и музыкой! {ICON_SPARKLE}\n\n"
                "**🧠 Чат с ИИ**\n"
                "• Отвечаю в ЛС или по упоминанию `@Бот`.\n"
                "• Использую современные LLM для диалога.\n\n"
                "**🎵 Музыкальные команды**\n"
                f"• `/play` — Поиск и выбор трека из списка\n"
                f"• `/search` — Быстрый запуск (живой поиск)\n"
                f"• `/link` — Играть по прямой ссылке\n"
                f"• `/playlist` — Загрузить весь плейлист\n"
                f"• `/nowplaying` — Открыть пульт управления\n"
                f"• `/queue` — Очередь треков\n\n"
                "**🎮 Пульт управления**\n"
                f"{e_prev} — Назад | {e_play}{e_pause} — Пауза/Плей | {e_next} — Вперед\n"
                f"{e_stop} — Стоп | {e_queue} — Очередь | {e_shuffle} — Шаттл | {e_loop} — Цикл\n\n"
                "**⚙️ Быстрое управление**\n"
                f"• `/skip` / `/previous` — Навигация\n"
                f"• `/pause` / `/resume` — Состояние\n"
                f"• `/stop` — Остановка и выход"
            ),
            color=discord.Color.from_rgb(88, 101, 242)
        )
        repo_url = "https://github.com/AndreyKilanov/llm_bot_admin/tree/main"
        embed.description += f"\n\n-# [{ICON_INFO} GitHub Repository]({repo_url})"
        await ctx.send(embed=embed)
