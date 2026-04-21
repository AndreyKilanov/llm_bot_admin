import asyncio
import logging
from typing import Optional

import discord
from discord import Message
from discord.ext import commands

from config import settings
from src.bot.discord.handlers import MessageHandler
from src.bot.discord.player import PlayerFactory
from src.bot.discord.views.constants import ui_config
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
            command_prefix=ui_config.default_prefix,
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
        """Регистрация глобальных обработчиков ошибок."""

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

    async def start(self) -> None:
        """Инициализация Opus и запуск основного цикла событий бота."""
        if not discord.opus.is_loaded():
            try:
                discord.opus.load_opus(ui_config.opus_path)
                logger.info("Opus загружен из: %s", ui_config.opus_path)
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
            await self.bot.load_extension("src.bot.discord.commands")
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
