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
        """Регистрация всех доступных команд."""
        
        @self.bot.hybrid_command(name="playmusic", description="Искать и играть музыку (YouTube)")
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

        # Интересует только переход «был в канале → вышел из канала»
        if not (before.channel and not after.channel):
            return

        player = PlayerFactory.get_player(member.guild.id, self.bot)
        if not player:
            return

        voice_handler = player.voice_handler

        # Штатный выход (/stop, /disconnect) — останавливаем плеер
        if voice_handler._intentional_disconnect:
            voice_handler._intentional_disconnect = False
            logger.info(
                "Штатный выход из голосового канала на сервере %d. Остановка плеера.",
                member.guild.id,
            )
            await player.stop()
            return

        # Принудительное выталкивание (server mute, kick из канала и т.д.) —
        # просто логируем. Плеер не трогаем, _voice_channel сохранён в VoiceHandler.
        # При следующей команде playmusic/link бот сам переподключится.
        logger.warning(
            "Бот принудительно выкинут из канала '%s' на сервере %d (server mute / kick). "
            "Плеер сохранён, ждём следующую команду.",
            before.channel.name,
            member.guild.id,
        )
