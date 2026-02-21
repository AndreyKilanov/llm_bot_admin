import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI
from tortoise.exceptions import DoesNotExist, IntegrityError, OperationalError

from src.web.app import create_app
from config import Settings


@pytest.fixture
def mock_bot():
    bot = AsyncMock()
    bot.get_me.return_value = AsyncMock(username="testbot", id=123)
    return bot


@pytest.fixture
def mock_dp():
    dp = AsyncMock()
    return dp


@pytest.fixture
def app(mock_bot, mock_dp):
    app_instance = create_app(mock_bot, mock_dp)
    
    # Add test routes to trigger exception handlers
    @app_instance.get("/test-404")
    async def exc_404():
        raise DoesNotExist("Not found")

    @app_instance.get("/test-422")
    async def exc_422():
        raise IntegrityError("Integrity")

    @app_instance.get("/test-500")
    async def exc_500():
        raise OperationalError("Operational")

    return app_instance


@pytest.mark.asyncio
async def test_healthcheck(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        
        response2 = await client.get("/health")
        assert response2.status_code == 200
        assert response2.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_exception_handlers(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r1 = await client.get("/test-404")
        assert r1.status_code == 404
        assert r1.json() == {"detail": "Not found"}
        
        r2 = await client.get("/test-422")
        assert r2.status_code == 422
        assert r2.json() == {"detail": "Integrity"}
        
        r3 = await client.get("/test-500")
        assert r3.status_code == 500
        assert r3.json() == {"detail": "Operational"}


@pytest.mark.asyncio
async def test_webhook_no_secret(app, mock_bot, mock_dp):
    settings = Settings()
    # Mock settings secret
    with patch("src.web.app.Settings") as mock_settings:
        mock_settings.return_value.WEBHOOK_SECRET = ""
        mock_settings.return_value.WEBHOOK_PATH = settings.WEBHOOK_PATH
        app_mocked = create_app(mock_bot, mock_dp)
        
        async with AsyncClient(transport=ASGITransport(app=app_mocked), base_url="http://test") as client:
            from aiogram.types import Update
            with patch("src.web.app.Update.model_validate") as mock_val:
                mock_val.return_value = AsyncMock()
                response = await client.post(
                    settings.WEBHOOK_PATH, 
                    json={"update_id": 1}
                )
                assert response.status_code == 200
                mock_dp.feed_update.assert_called_once()


@pytest.mark.asyncio
async def test_webhook_with_valid_secret(app, mock_bot, mock_dp):
    settings = Settings()
    with patch("src.web.app.Settings") as mock_settings:
        mock_settings.return_value.WEBHOOK_SECRET = "supersecret"
        mock_settings.return_value.WEBHOOK_PATH = settings.WEBHOOK_PATH
        app_mocked = create_app(mock_bot, mock_dp)
        
        async with AsyncClient(transport=ASGITransport(app=app_mocked), base_url="http://test") as client:
            with patch("src.web.app.Update.model_validate"):
                response = await client.post(
                    settings.WEBHOOK_PATH, 
                    json={"update_id": 1},
                    headers={"X-Telegram-Bot-Api-Secret-Token": "supersecret"}
                )
                assert response.status_code == 200
                mock_dp.feed_update.assert_called_once()


@pytest.mark.asyncio
async def test_webhook_with_invalid_secret(app, mock_bot, mock_dp):
    settings = Settings()
    with patch("src.web.app.Settings") as mock_settings:
        mock_settings.return_value.WEBHOOK_SECRET = "supersecret"
        mock_settings.return_value.WEBHOOK_PATH = settings.WEBHOOK_PATH
        app_mocked = create_app(mock_bot, mock_dp)
        
        async with AsyncClient(transport=ASGITransport(app=app_mocked), base_url="http://test") as client:
            response = await client.post(
                settings.WEBHOOK_PATH, 
                json={"update_id": 1},
                headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"}
            )
            assert response.status_code == 403
            mock_dp.feed_update.assert_not_called()
