from aiogram import Bot
from aiogram.types import Update
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from tortoise.contrib.fastapi import register_tortoise
from pathlib import Path
import logging

from config import Settings
from src.database.config import get_tortoise_config
from src.web.admin import router as admin_router


import asyncio

def create_app(bot: Bot, dp, use_webhook: bool = False) -> FastAPI:
    app = FastAPI()
    settings = Settings()
    static_path = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
    
    app.include_router(admin_router)
    register_tortoise(
        app,
        config=get_tortoise_config(),
        generate_schemas=False,
        add_exception_handlers=True,
    )

    @app.on_event("startup")
    async def startup() -> None:
        logger = logging.getLogger("bot.startup")
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
