import logging
from typing import Final

import discord
from discord import Message

from src.database.models import AllowedChat, Setting
from src.exceptions import ConfigurationError
from src.services import HistoryService, LLMService, SettingsService
from src.bot.discord.views.constants import ui_config

logger = logging.getLogger("discord.handlers")


class MessageHandler:
    """Класс для обработки сообщений Discord.

    Отвечает за фильтрацию входящих сообщений, проверку прав доступа (белые списки),
    взаимодействие с LLM сервисом и отправку ответов.
    """

    PLATFORM: Final[str] = "discord"

    def __init__(self, bot: discord.Client) -> None:
        """Инициализация обработчика сообщений.

        Args:
            bot: Экземпляр Discord бота.
        """
        self.bot: discord.Client = bot

    async def handle_message(self, message: Message) -> None:
        """Основной цикл обработки входящего сообщения.

        Args:
            message: Входящее сообщение Discord.
        """
        if not await self._should_process_message(message):
            return

        if not await self._is_allowed_to_respond(message):
            return

        user_text = await self._prepare_content(message)
        if not user_text:
            return

        logger.info("Входящее сообщение Discord от %s: %s", message.author, user_text)

        async with message.channel.typing():
            await self._process_interaction(message, user_text)

    async def _should_process_message(self, message: Message) -> bool:
        """Первичная фильтрация сообщений.

        Args:
            message: Сообщение для проверки.

        Returns:
            bool: True если сообщение следует обрабатывать дальше.
        """
        if message.author.id == getattr(self.bot.user, "id", None):
            return False

        if message.content.startswith("/"):
            return False

        if not await SettingsService.is_discord_bot_enabled():
            return False

        return True

    async def _is_allowed_to_respond(self, message: Message) -> bool:
        """Комплексная проверка прав доступа к обработке сообщения.

        Проверяет белый список каналов/гильдий, настройки DM и общие правила ответов.

        Args:
            message: Сообщение для проверки прав.

        Returns:
            bool: True если боту разрешено ответить.
        """
        chat_id = message.channel.id
        guild_id = message.guild.id if message.guild else None
        is_dm = isinstance(message.channel, discord.DMChannel)
        is_mentioned = self.bot.user in message.mentions or f"<@{self.bot.user.id}>" in message.content

        allowed_channel = await AllowedChat.get_or_none(chat_id=chat_id, platform=self.PLATFORM)
        allowed_guild = await AllowedChat.get_or_none(chat_id=guild_id, platform=self.PLATFORM) if guild_id else None

        if (allowed_channel and not allowed_channel.is_active) or (allowed_guild and not allowed_guild.is_active):
            logger.debug("Discord канал %s или сервер %s явно отключены.", chat_id, guild_id)
            return False

        is_channel_active = allowed_channel.is_active if allowed_channel else False
        is_guild_active = allowed_guild.is_active if allowed_guild else False
        is_in_whitelist = is_channel_active or is_guild_active

        if is_in_whitelist:
            if not is_dm and is_guild_active and not is_channel_active:
                await self._auto_activate_channel(message)
                
            respond_everyone = await SettingsService.should_respond_to_everyone()
            return is_dm or is_mentioned or respond_everyone

        return await self._check_new_chat_permissions(message, is_dm, is_mentioned)

    async def _check_new_chat_permissions(self, message: Message, is_dm: bool, is_mentioned: bool) -> bool:
        """Вспомогательная проверка прав для новых чатов.

        Args:
            message: Сообщение.
            is_dm: Флаг личного сообщения.
            is_mentioned: Флаг упоминания бота.

        Returns:
            bool: Результат проверки.
        """
        new_chats_setting = await Setting.get_or_none(key=ui_config.setting_allow_new_chats)
        allow_new_chats = str(new_chats_setting.value).lower() == "true" if new_chats_setting else False

        if not allow_new_chats:
            respond_everyone = await SettingsService.should_respond_to_everyone()
            return (is_mentioned or is_dm) and respond_everyone

        if is_dm:
            dm_setting = await Setting.get_or_none(key=ui_config.setting_allow_dms)
            return str(dm_setting.value).lower() == "true" if dm_setting else False
        respond_everyone = await SettingsService.should_respond_to_everyone()
        return is_mentioned or respond_everyone

    async def _auto_activate_channel(self, message: Message) -> None:
        """Автоматическая активация канала, если его гильдия в белом списке.

        Args:
            message: Сообщение из канала.
        """
        if not message.guild:
            return

        await AllowedChat.update_or_create(
            chat_id=message.channel.id,
            platform=self.PLATFORM,
            defaults={
                "is_active": True,
                "title": f"{message.guild.name} / {message.channel.name}"
            }
        )
        logger.info("Авто-активация канала %s (гильдия %s в белом списке)", message.channel.id, message.guild.id)

    async def _prepare_content(self, message: Message) -> str:
        """Очистка текста сообщения от упоминаний бота.

        Args:
            message: Сообщение.

        Returns:
            str: Очищенный текст.
        """
        user_text = message.clean_content
        if not self.bot.user:
            return user_text.strip()

        bot_names = [f"@{self.bot.user.name}"]
        if message.guild and message.guild.me.nick:
            bot_names.append(f"@{message.guild.me.nick}")

        for name in bot_names:
            user_text = user_text.replace(name, "")

        return user_text.strip()

    async def _process_interaction(self, message: Message, user_text: str) -> None:
        """Взаимодействие с LLM и отправка ответа.

        Args:
            message: Сообщение Discord.
            user_text: Очищенный текст пользователя.
        """
        chat_id = message.channel.id
        is_dm = isinstance(message.channel, discord.DMChannel)
        chat_type = "private" if is_dm else "guild"

        if is_dm:
            chat_title = f"DM: {message.author.name}"
        else:
            chat_title = f"{message.guild.name} / {message.channel.name}"

        try:
            mem_setting = await Setting.get_or_none(key=ui_config.setting_memory_limit)
            limit = int(mem_setting.value) if mem_setting else ui_config.default_memory_limit

            await HistoryService.add_message(
                chat_id=chat_id,
                role="user",
                content=user_text,
                platform=self.PLATFORM,
                chat_type=chat_type,
                title=chat_title,
                nickname=message.author.name
            )

            history = await HistoryService.get_last_messages(chat_id, platform=self.PLATFORM, limit=limit)
            response_text = await LLMService.generate_response(messages=history)

            await HistoryService.add_message(
                chat_id=chat_id,
                role="assistant",
                content=response_text,
                platform=self.PLATFORM,
                chat_type=chat_type,
                title=chat_title
            )

            await self._send_long_message(message.channel, response_text)

        except (ValueError, ConfigurationError) as e:
            await self._handle_config_error(message, e)
        except Exception as e:
            logger.exception("Критическая ошибка при генерации ответа LLM: %s", e)
            await message.channel.send(ui_config.msg_err_llm_internal)

    async def _send_long_message(self, channel: discord.abc.Messageable, text: str) -> None:
        """Отправка длинного сообщения путем разбиения на части.

        Args:
            channel: Канал для отправки.
            text: Текст ответа.
        """
        if len(text) <= ui_config.max_message_length:
            await channel.send(text)
            return

        for i in range(0, len(text), ui_config.max_message_length):
            await channel.send(text[i : i + ui_config.max_message_length])

    async def _handle_config_error(self, message: Message, error: Exception) -> None:
        """Обработка ошибок конфигурации и соединений.

        Args:
            message: Сообщение пользователя.
            error: Пойманное исключение.
        """
        error_msg = str(error)
        logger.warning("Проблема конфигурации в Discord обработчике: %s", error_msg)

        if "Отсутствует активное соединение" in error_msg:
            await message.channel.send(ui_config.msg_err_llm_connection)
        else:
            await message.channel.send(ui_config.msg_err_config_base.format(error_msg=error_msg))
