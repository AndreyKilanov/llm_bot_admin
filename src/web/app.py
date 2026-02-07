import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from aiogram import Bot
from aiogram.types import Update
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from starlette.responses import JSONResponse
from tortoise import Tortoise
from tortoise.exceptions import DoesNotExist, OperationalError, IntegrityError

from config import Settings
from src.bot.discord import discord_bot
from src.database.config import get_tortoise_config
from src.web.admin import router as admin_router


def create_app(bot: Bot, dp, use_webhook: bool = False) -> FastAPI:
    settings = Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger = logging.getLogger("bot.startup")
        await Tortoise.init(config=get_tortoise_config())
        logger.info("Tortoise ORM инициализирован")

        try:
            bot_user = await bot.get_me()
            logger.info("Бот успешно подключен: @%s (ID: %s)", bot_user.username, bot_user.id)
        except Exception as e:
            logger.error("Ошибка при проверке подключения бота: %s", e)

        if use_webhook:
            url = f"{settings.BASE_WEBHOOK_URL.rstrip('/')}{settings.WEBHOOK_PATH}"
            secret = settings.WEBHOOK_SECRET or None
            await bot.set_webhook(url, secret_token=secret)
            logger.info("Запуск в режиме WEBHOOK: %s", url)
        else:
            await bot.delete_webhook(drop_pending_updates=True)
            logger.info("Запуск в режиме POLLING (в фоне)")
            asyncio.create_task(dp.start_polling(bot))

        try:
            logger.info("Инициализация Discord бота...")
            asyncio.create_task(discord_bot.start())
        except Exception as e:
             logger.error(f"Не удалось запустить Discord бота: {e}")

        yield

        logger.info("Завершение работы приложения...")
        try:
            await discord_bot.stop()
            logger.info("Discord бот остановлен.")
        except Exception as e:
            logger.error(f"Ошибка при остановке Discord бота: {e}")

        await Tortoise.close_connections()
        logger.info("Tortoise ORM соединения закрыты")

    app = FastAPI(lifespan=lifespan)
    static_path = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
    
    app.include_router(admin_router)

    @app.exception_handler(DoesNotExist)
    async def does_not_exist_handler(request: Request, exc: DoesNotExist):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError):
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(OperationalError)
    async def operational_error_handler(request: Request, exc: OperationalError):
        return JSONResponse(status_code=500, content={"detail": str(exc)})

    @app.get("/")
    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.post(settings.WEBHOOK_PATH)
    async def webhook(request: Request) -> Response:
        body = await request.json()

        if settings.WEBHOOK_SECRET:
            secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
            if secret != settings.WEBHOOK_SECRET:
                return Response(status_code=403)

        update = Update.model_validate(body, context={"bot": bot})
        await dp.feed_update(bot, update)

        return Response(status_code=200)

    return app
