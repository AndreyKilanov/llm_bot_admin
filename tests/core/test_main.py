import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from src.main import init_db, close_db, main

@pytest.mark.asyncio
async def test_init_db():
    with patch("src.main.Tortoise.init", new_callable=AsyncMock) as mock_init:
        await init_db()
        mock_init.assert_called_once()

@pytest.mark.asyncio
async def test_close_db():
    with patch("src.main.Tortoise.close_connections", new_callable=AsyncMock) as mock_close:
        await close_db()
        mock_close.assert_called_once()

def test_main():
    with patch("src.main.Settings") as mock_settings, \
         patch("src.main.BaseLogger.setup") as mock_logger_setup, \
         patch("src.main.Bot") as mock_bot, \
         patch("src.main.Dispatcher") as mock_dp, \
         patch("src.main.create_app") as mock_create_app, \
         patch("src.main.uvicorn.run") as mock_uvicorn_run:
        
        # Setup mocks
        mock_settings_instance = MagicMock()
        mock_settings_instance.USE_WEBHOOK = False
        mock_settings_instance.TELEGRAM_PROXY_URL = None
        mock_settings_instance.BOT_TOKEN = "test_token"
        mock_settings_instance.HOST = "127.0.0.1"
        mock_settings_instance.PORT = 8000
        mock_settings.return_value = mock_settings_instance
        
        main()
        
        mock_logger_setup.assert_called_once()
        mock_bot.assert_called_once()
        mock_dp.assert_called_once()
        mock_create_app.assert_called_once()
        mock_uvicorn_run.assert_called_once()
