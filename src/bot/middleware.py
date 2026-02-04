import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.enums import ChatType
from aiogram.types import Message

from src.database.models import AllowedChat, Setting

logger = logging.getLogger("bot.middleware")


class LoggingMiddleware(BaseMiddleware):
    """Middleware для логирования входящих сообщений."""

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        message = event
        user_id = message.from_user.id if message.from_user else "Unknown"
        username = message.from_user.username if message.from_user else "None"
        text = message.text or "[Non-text message]"
        
        logger.info(
            "Сообщение от %s (@%s): %s",
            user_id,
            username,
            text
        )
            
        return await handler(event, data)


class WhitelistMiddleware(BaseMiddleware):
    """Middleware для проверки разрешенных групп и активности бота."""

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        message = event

        enabled_setting = await Setting.get_or_none(key="telegram_bot_enabled")
        is_bot_enabled = str(enabled_setting.value).lower() == "true" if enabled_setting else True
        
        if not is_bot_enabled:
            logger.debug("Telegram бот выключен в настройках, игнорируем сообщение.")
            return

        if message.chat.type == ChatType.PRIVATE:
            setting = await Setting.get_or_none(key="allow_private_chat")
            is_allowed = str(setting.value).lower() == "true" if setting else True
            
            if not is_allowed:
                 logger.debug("Личные сообщения запрещены в настройках.")
                 return
            return await handler(event, data)

        if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
            chat_id = message.chat.id
            allowed = await AllowedChat.filter(chat_id=chat_id, platform="telegram", is_active=True).exists()
            
            if not allowed:
                logger.warning("Группа %s (%s) не в белом списке.", message.chat.title, chat_id)
                return
            
            logger.debug(f"Группа {message.chat.title} разрешена")

        return await handler(event, data)
