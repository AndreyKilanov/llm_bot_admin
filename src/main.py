import asyncio
import logging
from contextlib import asynccontextmanager

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from tortoise import Tortoise

from config import Settings
from src.bot import handlers
from src.bot.middleware import LoggingMiddleware, WhitelistMiddleware
from src.database.config import get_tortoise_config
from src.logger import BaseLogger
from src.web.app import create_app


async def init_db() -> None:
    """Инициализация базы данных."""
    config = get_tortoise_config()
    await Tortoise.init(config=config)


async def close_db() -> None:
    """Закрытие соединений с базой данных."""
    await Tortoise.close_connections()


def main() -> None:
    """Основная функция запуска бота."""
    settings = Settings()
    use_webhook = settings.USE_WEBHOOK
    BaseLogger.setup()
    logger = logging.getLogger("bot.startup")

    session = None
    if settings.TELEGRAM_PROXY_URL:
        session = AiohttpSession(proxy=settings.TELEGRAM_PROXY_URL)

    bot = Bot(token=settings.BOT_TOKEN, session=session)
    dp = Dispatcher()
    dp.include_router(handlers.router)
    dp.message.middleware(LoggingMiddleware())
    dp.message.middleware(WhitelistMiddleware())

    # Запускаем FastAPI приложение, которое само решит, как запустить бота (webhook или фоновый polling)
    app = create_app(bot, dp, use_webhook=use_webhook)
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)


if __name__ == "__main__":
    main()
