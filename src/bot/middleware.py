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
            return None

        chat_id = message.chat.id
        allowed_chat = await AllowedChat.get_or_none(chat_id=chat_id, platform="telegram")

        if allowed_chat:
            if not allowed_chat.is_active:
                logger.debug(f"Чат {chat_id} явно отключен в белом списке.")
                return None

            return await handler(event, data)

        new_chats_setting = await Setting.get_or_none(key="telegram_allow_new_chats")
        allow_new_chats = str(new_chats_setting.value).lower() == "true" if new_chats_setting else True

        if not allow_new_chats:
            logger.warning(f"Чат {chat_id} не в белом списке и добавление новых чатов запрещено.")
            return None

        if message.chat.type == ChatType.PRIVATE:
            setting = await Setting.get_or_none(key="allow_private_chat")
            is_private_allowed = str(setting.value).lower() == "true" if setting else True
            
            if not is_private_allowed:
                 logger.debug("Личные сообщения запрещены в настройках.")
                 return None

        return await handler(event, data)
