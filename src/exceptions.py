
class BotBaseException(Exception):
    """Базовое исключение для проекта."""
    pass

class ConfigurationError(BotBaseException):
    """Ошибка конфигурации (отсутствие ключей, активных соединений и т.д.)."""
    pass

class ServiceError(BotBaseException):
    """Ошибка при выполнении логики сервиса."""
    pass
