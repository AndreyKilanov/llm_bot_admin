import logging

import discord
from discord import Message

from src.database.models import AllowedChat, Setting
from src.services.history_service import HistoryService
from src.services.llm_service import LLMService

logger = logging.getLogger("discord.handlers")


class MessageHandler:
    """Класс для обработки сообщений Discord."""
    
    def __init__(self, bot: discord.Client):
        """
        Инициализация обработчика сообщений.
        
        Args:
            bot: Экземпляр Discord бота
        """
        self.bot = bot
    
    async def handle_message(self, message: Message) -> None:
        """
        Обработка входящего сообщения.
        
        Args:
            message: Входящее сообщение Discord
        """
        if message.author == self.bot.user:
            return

        if message.content.startswith("/"):
            return

        enabled_setting = await Setting.get_or_none(key="discord_bot_enabled")
        if enabled_setting and str(enabled_setting.value).lower() != "true":
            return

        chat_id = message.channel.id
        is_dm = isinstance(message.channel, discord.DMChannel)
        is_mentioned = (self.bot.user in message.mentions or
                        f"<@{self.bot.user.id}>" in message.content)
        guild_id = message.guild.id if message.guild else None
        allowed_channel = await AllowedChat.get_or_none(chat_id=chat_id, platform="discord")
        allowed_guild = await AllowedChat.get_or_none(chat_id=guild_id, platform="discord") if guild_id else None

        if allowed_channel and not allowed_channel.is_active:
            logger.debug(f"Discord канал {chat_id} явно отключен в белом списке.")
            return

        if allowed_guild and not allowed_guild.is_active:
            logger.debug(f"Discord сервер {guild_id} явно отключен в белом списке.")
            return

        is_channel_active = allowed_channel.is_active if allowed_channel else False
        is_guild_active = allowed_guild.is_active if allowed_guild else False
        is_in_whitelist = is_channel_active or is_guild_active

        if not is_in_whitelist:
            new_chats_setting = await Setting.get_or_none(key="discord_allow_new_chats")
            allow_new_chats = str(
                new_chats_setting.value).lower() == "true" if new_chats_setting else False

            if not allow_new_chats:
                return

            if is_dm:
                dm_setting = await Setting.get_or_none(key="discord_allow_dms")
                if not dm_setting or str(dm_setting.value).lower() != "true":
                    return
            else:
                if not is_mentioned:
                    return

        if not is_dm and is_guild_active and not is_channel_active:
            await AllowedChat.update_or_create(
                chat_id=chat_id,
                platform="discord",
                defaults={"is_active": True,
                          "title": f"{message.guild.name} / {message.channel.name}"}
            )
            logger.info(f"Auto-activated channel {chat_id} because guild {guild_id} is whitelisted")

        user_text = message.clean_content

        if self.bot.user:
            bot_name = self.bot.user.name
            user_text = user_text.replace(f"@{bot_name}", "")

            if message.guild and message.guild.me.nick:
                user_text = user_text.replace(f"@{message.guild.me.nick}", "")

        user_text = user_text.strip()

        if not user_text:
            return

        logger.info(f"Incoming Discord message from {message.author}: {user_text}")

        async with message.channel.typing():
            try:
                mem_setting = await Setting.get_or_none(key="discord_memory_limit")
                limit = int(mem_setting.value) if mem_setting else 10
                chat_type = "private" if is_dm else "guild"

                if is_dm:
                    chat_title = f"DM: {message.author.name}"
                else:
                    chat_title = f"{message.guild.name} / {message.channel.name}"

                nickname = message.author.name

                await HistoryService.add_message(
                    chat_id, "user", user_text,
                    platform="discord", chat_type=chat_type,
                    title=chat_title,
                    nickname=nickname
                )
                history = await HistoryService.get_last_messages(chat_id, platform="discord", limit=limit)
                response_text = await LLMService.generate_response(messages=history)
                await HistoryService.add_message(
                    chat_id, "assistant", response_text,
                    platform="discord", chat_type=chat_type,
                    title=chat_title,
                    nickname=None
                )

                if len(response_text) > 2000:
                    for i in range(0, len(response_text), 2000):
                        await message.channel.send(response_text[i:i + 2000])
                else:
                    await message.channel.send(response_text)

            except ValueError as e:
                error_msg = str(e)
                logger.error(f"Validation/Config error in Discord handler: {error_msg}")
                if "Отсутствует активное соединение" in error_msg:
                    await message.channel.send("❌ Отсутствует активное соединение с LLM API")
                else:
                    await message.channel.send(f"❌ Ошибка конфигурации: {error_msg}")
            except Exception as e:
                logger.error(f"Error generating response: {e}")
                await message.channel.send("❌ Отсутствует активное соединение с LLM API или сервис недоступен")
