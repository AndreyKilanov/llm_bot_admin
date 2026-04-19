import asyncio
import logging
from typing import Optional

import discord
from discord import Message
from discord.ext import commands

from config import settings
from src.bot.discord.handlers import MessageHandler
from src.bot.discord.player import PlayerFactory
from .constants import OPUS_PATH, DEFAULT_PREFIX
from .commands import CommandHandlers
from src.bot.discord.views.emoji_manager import emoji_manager

logger = logging.getLogger("discord.bot")


class DiscordBot:
    """Главный класс для управления базовой инфраструктурой Discord бота."""

    def __init__(self) -> None:
        """Инициализация бота и базовых компонентов."""
        intents = discord.Intents.default()
        intents.messages = True
        intents.guilds = True
        intents.message_content = True
        intents.dm_messages = True
        intents.voice_states = True

        self.bot = commands.Bot(
            command_prefix=DEFAULT_PREFIX,
            intents=intents,
            help_command=None
        )
        self.bot.on_ready = self.on_ready
        self.bot.on_message = self.on_message
        self.bot.on_voice_state_update = self.on_voice_state_update
        self.message_handler = MessageHandler(self.bot)

        self._register_commands()
        self.bg_task: Optional[asyncio.Task] = None

    def _register_commands(self) -> None:
        """Регистрация всех доступных команд и глобальных обработчиков ошибок."""

        @self.bot.event
        async def on_command_error(ctx: commands.Context, error: Exception) -> None:
            """Глобальный обработчик ошибок hybrid-команд (ext.commands)."""
            cause = error
            for _ in range(4):
                if hasattr(cause, "original") and cause.original is not None:
                    cause = cause.original
                else:
                    break
            if isinstance(cause, discord.NotFound) and cause.code == 10062:
                logger.warning(
                    "on_command_error [%s]: interaction устарел (10062), пропускаем.",
                    getattr(ctx.command, "name", "?"),
                )
                return
            logger.error("Ошибка команды '%s': %s", ctx.command, error)

        @self.bot.tree.error
        async def on_tree_error(
            interaction: discord.Interaction,
            error: discord.app_commands.AppCommandError,
        ) -> None:
            """Глобальный обработчик ошибок слэш-команд (app_commands)."""
            cause = error.original if hasattr(error, "original") else error
            if isinstance(cause, discord.NotFound) and cause.code == 10062:
                logger.debug(
                    "on_tree_error [%s]: interaction устарел (10062), пропускаем.",
                    getattr(interaction.command, "name", "?"),
                )
                return
            logger.error("Ошибка слэш-команды '%s': %s", getattr(interaction.command, "name", "?"), error)

        @self.bot.hybrid_command(name="play", description="Искать и играть музыку (YouTube)")
        async def play_music_cmd(ctx: commands.Context, *, query: str):
            await ctx.defer()
            await CommandHandlers.handle_playmusic(self.bot, ctx, query)

        @self.bot.hybrid_command(name="link", description="Играть по ссылке YouTube")
        async def play_link_cmd(ctx: commands.Context, *, url: str):
            await ctx.defer()
            await CommandHandlers.handle_link(self.bot, ctx, url)

        @self.bot.hybrid_command(name="playlist", description="Загрузить плейлист по ссылке YouTube")
        async def play_playlist_cmd(ctx: commands.Context, *, url: str):
            await ctx.defer()
            await CommandHandlers.handle_playlist(self.bot, ctx, url)

        @self.bot.hybrid_command(name="skip", description="К следующему треку")
        async def skip_cmd(ctx: commands.Context):
            await CommandHandlers.handle_skip(self.bot, ctx)

        @self.bot.hybrid_command(name="previous", description="К предыдущему треку")
        async def previous_cmd(ctx: commands.Context):
            await CommandHandlers.handle_previous(self.bot, ctx)

        @self.bot.hybrid_command(name="pause", description="Поставить на паузу")
        async def pause_cmd(ctx: commands.Context):
            await CommandHandlers.handle_pause(self.bot, ctx)

        @self.bot.hybrid_command(name="resume", description="Продолжить музыку")
        async def resume_cmd(ctx: commands.Context):
            await CommandHandlers.handle_resume(self.bot, ctx)

        @self.bot.hybrid_command(name="stop", description="Остановка и выход")
        async def stop_cmd(ctx: commands.Context):
            await CommandHandlers.handle_stop(self.bot, ctx)

        @self.bot.hybrid_command(name="queue", description="Очередь треков")
        async def queue_cmd(ctx: commands.Context):
            await CommandHandlers.handle_queue(self.bot, ctx)

        @self.bot.hybrid_command(name="nowplaying", description="Текущий трек")
        async def nowplaying_cmd(ctx: commands.Context):
            await CommandHandlers.handle_nowplaying(self.bot, ctx)

        @self.bot.hybrid_command(name="help", description="Справка по боту")
        async def help_cmd(ctx: commands.Context):
            await CommandHandlers.handle_help(ctx)

        @self.bot.tree.command(name="search", description="Живой поиск музыки в YouTube")
        @discord.app_commands.describe(query="Введите название трека или выберите из списка")
        async def search_slash(interaction: discord.Interaction, query: str) -> None:
            """Слэш-команда поиска. Если выбран трек из списка — сразу добавляет и включает."""
            try:
                await interaction.response.defer()
            except discord.NotFound:
                return
            await CommandHandlers.handle_search(self.bot, interaction, query)

        @search_slash.autocomplete("query")
        async def search_autocomplete(
            interaction: discord.Interaction, current: str
        ) -> list[discord.app_commands.Choice[str]]:
            """Живой поиск треков для автодополнения с жестким таймаутом."""
            try:
                if not current.strip():
                    return []

                from src.services import music_service, SettingsService
                import time
                start_time = time.monotonic()

                if not await SettingsService.is_discord_bot_enabled():
                    return []
                if not await SettingsService.is_discord_music_enabled():
                    return []

                tracks = await music_service.search_tracks_fast(current, max_results=10)
                elapsed = time.monotonic() - start_time
                logger.info(f"Сверхбыстрый YouTube поиск: '{current}' -> {len(tracks)} треков за {elapsed:.3f}с")

                choices = []
                # Всегда подсовываем то, что ввел пользователь, чтобы он точно мог запустить обычный поиск
                choices.append(discord.app_commands.Choice(name=f"🔍 Искать: {current}"[:100], value=current[:100]))

                for t in tracks[:9]:
                    title = t["title"][:80]
                    uploader = t.get("uploader", "YouTube")[:15]
                    name = f"{title} | {uploader}"
                    choices.append(discord.app_commands.Choice(name=name, value=t["url"]))

                return choices
            except Exception as e:
                logger.error(f"Аварийная ошибка в автодополнении поиска для '{current}': {e}", exc_info=True)
                # Фолбэк, чтобы интерфейс Discord не блокировался
                return [discord.app_commands.Choice(name=current[:100], value=current[:100])] if current.strip() else []

    async def start(self) -> None:
        """Инициализация Opus и запуск основного цикла событий бота."""
        if not discord.opus.is_loaded():
            try:
                discord.opus.load_opus(OPUS_PATH)
                logger.info("Opus загружен из: %s", OPUS_PATH)
            except Exception as e:
                logger.error("Ошибка загрузки Opus: %s", e)
        else:
            logger.info("Opus уже загружен.")

        token = settings.DISCORD_BOT_TOKEN
        if token:
            token = token.strip().strip('"').strip("'")

        if not token or token.lower() in ("none", "your_token_here", ""):
            logger.warning("Discord токен не обнаружен.")
            return

        logger.info("Запуск Discord бота...")
        try:
            await self.bot.start(token)
        except Exception as e:
            logger.error("Не удалось запустить бота: %s", e)

    async def stop(self) -> None:
        """Остановка всех плееров и закрытие соединения."""
        players = list(PlayerFactory.get_all_players().values())
        for player in players:
            try:
                await player.disconnect()
                PlayerFactory.remove_player(player.guild_id)
            except Exception as e:
                logger.error("Ошибка при остановке плеера %s: %s", player.guild_id, e)

        if self.bot:
            await self.bot.close()

    async def on_ready(self) -> None:
        """Событие готовности бота."""
        logger.info("Discord Bot подключен как %s", self.bot.user)
        
        try:
            await emoji_manager.initialize(self.bot)
        except Exception as e:
            logger.error("Ошибка при инициализации EmojiManager: %s", e)

        try:
            synced = await self.bot.tree.sync()
            logger.info("Slash-команды синхронизированы: %d", len(synced))
        except Exception as e:
            logger.error("Ошибка синхронизации: %s", e)

    async def on_message(self, message: Message) -> None:
        """Обработка команд и диалога с LLM."""
        await self.bot.process_commands(message)
        await self.message_handler.handle_message(message)

    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState) -> None:
        """Событие изменения состояния голоса.

        Различает два сценария:

        - **Штатный выход** (через команду ``/stop``) — определяется флагом
          ``VoiceHandler._intentional_disconnect``. Плеер полностью останавливается.
        - **Принудительное выталкивание** (server mute, kick из канала и т.п.) —
          игнорируется. Плеер не трогается, последний канал сохраняется.
          Следующая команда воспроизведения сама переподключит бота.
        """
        if member.id != self.bot.user.id:
            return

        if not (before.channel and not after.channel):
            return

        player = PlayerFactory.get_player(member.guild.id, self.bot)
        if not player:
            return

        voice_handler = player.voice_handler

        if getattr(voice_handler, '_intentional_disconnect', False) or getattr(voice_handler, '_is_connecting', False):
            return

        logger.warning(
            "Бот покинул канал '%s' на сервере %d. Очистка плеера.",
            before.channel.name,
            member.guild.id,
        )
        await player.disconnect()
