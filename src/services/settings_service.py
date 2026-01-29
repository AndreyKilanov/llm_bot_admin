from config import Settings
from src.database import Setting
from src.logger import log_function


KEY_SYSTEM_PROMPT = "system_prompt"


class SettingsService:
    """Сервис для управления настройками бота."""

    @staticmethod
    @log_function
    async def get_system_prompt() -> str:
        """Возвращает системный промпт из БД или из настроек по умолчанию."""
        setting = await Setting.get_or_none(key=KEY_SYSTEM_PROMPT)
        if setting:
            return setting.value
        return Settings().SYSTEM_PROMPT

    @staticmethod
    @log_function
    async def set_system_prompt(content: str) -> None:
        """Сохраняет системный промпт в БД."""
        await Setting.update_or_create(defaults={"value": content}, key=KEY_SYSTEM_PROMPT)

