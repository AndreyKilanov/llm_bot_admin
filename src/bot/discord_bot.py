import asyncio
import logging
from typing import Optional

import discord
from discord import Message

from config import settings
from src.database.models import AllowedChat, Setting
from src.services.history_service import HistoryService
from src.services.llm_service import LLMService

logger = logging.getLogger("discord.bot")


class DiscordBot:
    def __init__(self):
        intents = discord.Intents.default()
        intents.messages = True
        intents.guilds = True
        intents.message_content = True  # Required for reading message content
        intents.dm_messages = True

        self.client = discord.Client(intents=intents)
        self.client.on_ready = self.on_ready
        self.client.on_message = self.on_message
        self.bg_task: Optional[asyncio.Task] = None

    async def start(self):
        """Starts the Discord bot."""
        token = settings.DISCORD_BOT_TOKEN
        if token:
            token = token.strip().strip('"').strip("'")
            
        if not token or token.lower() in ("none", "your_token_here", ""):
            logger.warning("Discord token не указан или имеет недопустимое значение. Discord бот не будет запущен.")
            return

        logger.info("Starting Discord bot...")
        try:
            await self.client.start(token)
        except Exception as e:
            logger.error(f"Failed to start Discord bot: {e}")

    async def stop(self):
        """Stops the Discord bot."""
        if self.client:
            await self.client.close()

    async def on_ready(self):
        logger.info(f"Discord Bot connected as {self.client.user}")

    async def on_message(self, message: Message):
        if message.author == self.client.user:
            return

        enabled_setting = await Setting.get_or_none(key="discord_bot_enabled")
        if enabled_setting and str(enabled_setting.value).lower() != "true":
            return

        chat_id = message.channel.id
        is_dm = isinstance(message.channel, discord.DMChannel)
        is_mentioned = (
                self.client.user in message.mentions or
                f"<@{self.client.user.id}>" in message.content
        )
        guild_id = message.guild.id if message.guild else None
        
        if is_dm:
            dm_setting = await Setting.get_or_none(key="discord_allow_dms")
            if not dm_setting or str(dm_setting.value).lower() != "true":
                return
        else:
            allowed_channel = await AllowedChat.get_or_none(chat_id=chat_id, platform="discord")
            allowed_guild = await AllowedChat.get_or_none(chat_id=guild_id, platform="discord") if guild_id else None
            is_channel_active = allowed_channel.is_active if allowed_channel else False
            is_guild_active = allowed_guild.is_active if allowed_guild else False
            allowed = is_channel_active or is_guild_active

            if not allowed and not is_mentioned:
                return

            if not is_mentioned:
                return

            if is_guild_active and not is_channel_active:
                await AllowedChat.update_or_create(
                    chat_id=chat_id, 
                    platform="discord", 
                    defaults={
                        "is_active": True, 
                        "title": f"{message.guild.name} / {message.channel.name}"
                    }
                )
                logger.info(f"Auto-activated channel {chat_id} because guild {guild_id} is whitelisted")

        user_text = message.clean_content

        if self.client.user:
            bot_name = self.client.user.name
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
                        await message.channel.send(response_text[i:i+2000])
                else:
                    await message.channel.send(response_text)
                    
            except Exception as e:
                logger.error(f"Error generating response: {e}")
                await message.channel.send("Произошла ошибка при обработке запроса.")

discord_bot = DiscordBot()
