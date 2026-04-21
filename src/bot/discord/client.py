import asyncio
import logging
from typing import Optional

import discord
from discord import Message
from discord.ext import commands

from config import settings
from src.bot.discord.handlers import MessageHandler
from src.bot.discord.player import PlayerFactory
from src.services import SettingsService
from src.bot.discord.views.constants import ui_config
from src.bot.discord.views.emoji_manager import emoji_manager
from src.services.player_state_service import PlayerStateService

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
        self._setup_global_checks()
        self.bg_task: Optional[asyncio.Task] = None

    def _setup_global_checks(self) -> None:
        """Настройка глобальных проверок доступности бота."""

        @self.bot.check
        async def global_enabled_check(ctx: commands.Context) -> bool:
            """Проверка для текстовых и гибридных команд."""
            is_enabled = await SettingsService.is_discord_bot_enabled()
            logger.info("Глобальная проверка (Prefix): BOT_ENABLED=%s", is_enabled)
            if not is_enabled:
                await ctx.send(ui_config.msg_bot_disabled, ephemeral=True)
                if ctx.guild:
                    player = PlayerFactory.get_player(ctx.guild.id, self.bot)
                    if player and player.is_connected:
                        await player.disconnect()
                        logger.info("Бот отключен на сервере %d (Prefix) из-за блокировки.", ctx.guild.id)
                return False
            return True

        async def global_tree_check(interaction: discord.Interaction) -> bool:
            """Проверка для всех слэш-команд."""
            is_enabled = await SettingsService.is_discord_bot_enabled()
            logger.info("Глобальная проверка (Interaction): BOT_ENABLED=%s", is_enabled)
            if not is_enabled:
                if not interaction.response.is_done():
                    await interaction.response.send_message(ui_config.msg_bot_disabled, ephemeral=True)
                else:
                    await interaction.followup.send(ui_config.msg_bot_disabled, ephemeral=True)
                
                if interaction.guild:
                    player = PlayerFactory.get_player(interaction.guild.id, self.bot)
                    if player and player.is_connected:
                        await player.disconnect()
                        logger.info("Бот отключен на сервере %d (Interaction) из-за блокировки.", interaction.guild.id)
                return False
            
            return True

        self.bot.tree.interaction_check = global_tree_check

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

        await self._cleanup_stale_players()

    async def _cleanup_stale_players(self) -> None:
        """Находит и удаляет все сообщения плееров, оставшиеся от прошлых сессий."""
        logger.info("Запуск глобальной очистки сообщений плееров...")
        states = await PlayerStateService.get_all_player_states()
        for guild_id, ch_id, msg_id in states:
            try:
                channel = self.bot.get_channel(ch_id) or await self.bot.fetch_channel(ch_id)
                if isinstance(channel, discord.TextChannel):
                    try:
                        msg = await channel.fetch_message(msg_id)
                        await msg.delete()
                        logger.info("Удалено устаревшее сообщение плеера на сервере %d", guild_id)
                    except discord.NotFound:
                        pass
                await PlayerStateService.clear_player_msg(guild_id)
            except Exception as e:
                logger.debug("Не удалось удалить сообщение %d в канале %d: %s", msg_id, ch_id, e)

    async def on_message(self, message: Message) -> None:
        """Обработка команд и диалога с LLM."""
        is_enabled = await SettingsService.is_discord_bot_enabled()
        if not is_enabled:
            # Если бот выключен — даже не пытаемся парсить команды или LLM
            is_mentioned = self.bot.user in message.mentions or f"<@{self.bot.user.id}>" in message.content
            if is_mentioned:
                logger.info("Бот упомянут, но выключен. Отправка уведомления.")
                try:
                    await message.channel.send(ui_config.msg_bot_disabled)
                except Exception:
                    pass
            return

        await self.bot.process_commands(message)
        await self.message_handler.handle_message(message)

    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState) -> None:
        """Событие изменения состояния голоса.
        
        Обрабатывает два случая:
        1. Бот сам покинул канал (выгнали или таймаут).
        2. Последний человек покинул канал (бот остался один).
        """
        if member.id == self.bot.user.id:
            if before.channel and not after.channel:
                player = PlayerFactory.get_player(member.guild.id, self.bot)
                if not player:
                    return
                
                voice_handler = player.voice_handler
                if not getattr(voice_handler, '_intentional_disconnect', False) and not getattr(voice_handler, '_is_connecting', False):
                    logger.warning(
                        "Бот был принудительно отключен от канала '%s' на сервере %d. Очистка.",
                        before.channel.name,
                        member.guild.id,
                    )
                    await player.disconnect()
            return

        if before.channel:
            player = PlayerFactory.get_player(member.guild.id, self.bot)
            if not player or not player.is_connected:
                return
            vc = player.voice_client
            if vc and vc.channel and vc.channel.id == before.channel.id:
                if player.voice_handler.is_alone():
                    logger.info(
                        "Последний пользователь покинул канал '%s' на сервере %d. Мгновенное отключение.",
                        before.channel.name,
                        member.guild.id,
                    )
                    await player.disconnect()
