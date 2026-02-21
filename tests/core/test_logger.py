import logging
import pytest
from unittest.mock import patch, MagicMock
from src.logger.base import BaseLogger
from src.logger.decorator import log_function
from src.exceptions import BotBaseException

@pytest.fixture(autouse=True)
def reset_logger():
    # To reset the singleton style initialization
    BaseLogger._initialized = False
    
    # Also clean up root logger handlers to avoid mock polluting real logs
    import logging
    root = logging.getLogger()
    old_handlers = list(root.handlers)
    root.handlers.clear()
    
    yield
    
    BaseLogger._initialized = False
    root.handlers.clear()
    for h in old_handlers:
        root.addHandler(h)

def test_base_logger_setup():
    with patch('src.logger.base.Path') as MockPath, \
         patch('src.logger.base.Settings') as MockSettings, \
         patch('src.logger.base.logging.StreamHandler') as MockStreamHandler, \
         patch('src.logger.base.logging.FileHandler') as MockFileHandler:
        
        mock_settings = MockSettings.return_value
        mock_settings.LOG_FILE_PATH = "logs/test.log"
        
        mock_stream = MockStreamHandler.return_value
        mock_stream.level = logging.INFO
        mock_file = MockFileHandler.return_value
        mock_file.level = logging.DEBUG
        
        # Call setup multiple times to test _initialized flag
        BaseLogger.setup()
        BaseLogger.setup()
        
        # Ensure it only initializes once
        MockPath.assert_called_once_with("logs/test.log")
        
def test_base_logger_get_logger():
    with patch('src.logger.base.BaseLogger.setup') as mock_setup:
        logger = BaseLogger.get_logger("test_logger")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_logger"
        mock_setup.assert_called_once()
        
        BaseLogger._initialized = True
        logger2 = BaseLogger.get_logger("test_logger2")
        assert mock_setup.call_count == 1 # Setup not called again

@pytest.mark.asyncio
async def test_log_function_async_success():
    with patch('src.logger.decorator.logging.getLogger') as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        @log_function
        async def dummy_async_func(x):
            return x * 2

        res = await dummy_async_func(5)
        
        assert res == 10
        mock_logger.debug.assert_called()
        mock_logger.info.assert_called()

@pytest.mark.asyncio
async def test_log_function_async_bot_exception():
    with patch('src.logger.decorator.logging.getLogger') as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        @log_function
        async def dummy_async_func():
            raise BotBaseException("Expected error")

        with pytest.raises(BotBaseException):
            await dummy_async_func()
            
        mock_logger.warning.assert_called()

@pytest.mark.asyncio
async def test_log_function_async_critical_exception():
    with patch('src.logger.decorator.logging.getLogger') as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        @log_function
        async def dummy_async_func():
            raise ValueError("Critical error")

        with pytest.raises(ValueError):
            await dummy_async_func()
            
        mock_logger.error.assert_called()

def test_log_function_sync_success():
    with patch('src.logger.decorator.logging.getLogger') as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        @log_function
        def dummy_sync_func(x):
            return x * 2

        res = dummy_sync_func(5)
        
        assert res == 10
        mock_logger.debug.assert_called()
        mock_logger.info.assert_called()

def test_log_function_sync_bot_exception():
    with patch('src.logger.decorator.logging.getLogger') as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        @log_function
        def dummy_sync_func():
            raise BotBaseException("Expected error")

        with pytest.raises(BotBaseException):
            dummy_sync_func()
            
        mock_logger.warning.assert_called()

def test_log_function_sync_critical_exception():
    with patch('src.logger.decorator.logging.getLogger') as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        @log_function
        def dummy_sync_func():
            raise ValueError("Critical error")

        with pytest.raises(ValueError):
            dummy_sync_func()
            
        mock_logger.error.assert_called()
