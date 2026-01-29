import logging
import sys
from pathlib import Path
from config import Settings

class BaseLogger:
    """Базовый класс для настройки логирования."""

    _initialized = False

    @classmethod
    def setup(cls) -> None:
        """Настройка базовой конфигурации логирования."""
        if cls._initialized:
            return

        settings = Settings()
        log_file = Path(settings.LOG_FILE_PATH)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # Формат для консоли (с указанием сервиса/имени логгера)
        console_formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # Формат для файла
        file_formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(logging.INFO)

        # File handler
        file_handler = logging.FileHandler(settings.LOG_FILE_PATH, encoding="utf-8")
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.DEBUG)

        # Настройка корневого логгера
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        
        # Очистка существующих хендлеров (чтобы не дублировать при перезапусках)
        if root_logger.hasHandlers():
            root_logger.handlers.clear()
            
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)

        cls._initialized = True
        logging.info("Система логирования инициализирована. Файл: %s", settings.LOG_FILE_PATH)

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """Возвращает настроенный логгер для конкретного сервиса."""
        if not BaseLogger._initialized:
            BaseLogger.setup()
        return logging.getLogger(name)
