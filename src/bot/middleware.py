import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.enums import ChatType
from aiogram.types import Message, Update

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
    """Middleware для проверки разрешенных групп."""

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        message = event
        
        # Разрешаем личные сообщения, если включена настройка
        if message.chat.type == ChatType.PRIVATE:
            setting = await Setting.get_or_none(key="allow_private_chat")
            is_allowed = str(setting.value).lower() == "true" if setting else True
            
            if not is_allowed:
                 return
            return await handler(event, data)

        # Для групп проверяем наличие в базе
        if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
            chat_id = message.chat.id
            logger.info(f"Проверка группы: {message.chat.title} (ID: {chat_id})")
            
            allowed = await AllowedChat.filter(chat_id=chat_id, is_active=True).exists()
            
            if not allowed:
                logger.warning("Попытка использования бота в неразрешенной группе: %s (%s)", message.chat.title, chat_id)
                await message.answer("Этот чат не авторизован для использования бота.")
                return
            
            logger.info(f"Группа {message.chat.title} ({chat_id}) разрешена")

        return await handler(event, data)
