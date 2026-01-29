from src.database.models import LLMConnection, LLMPrompt
from src.logger import log_function
from src.llm.openrouter import validate_key

class LLMService:
    """Сервис для управления подключениями к LLM и их промптами."""

    @staticmethod
    @log_function
    async def check_connection(connection_id: int) -> bool:
        """Проверяет работоспособность подключения.

        Args:
            connection_id: ID подключения

        Returns:
            True если успешно, False если ошибка.
        """
        conn = await LLMConnection.get_or_none(id=connection_id)
        if not conn:
            return False
        
        if conn.provider.lower() == "openrouter":
            return await validate_key(conn.api_key)
        
        if conn.base_url:
            from src.llm.openrouter import validate_generic_key
            return await validate_generic_key(conn.api_key, conn.base_url)
        
        from src.logger import get_logger
        get_logger("llm_service").warning(f"Connection check failed: provider '{conn.provider}' not supported for validation and no base_url")
        return False

    @staticmethod
    async def check_temporary_connection(provider: str, api_key: str, base_url: str | None = None) -> bool:
        """Проверяет работоспособность данных подключения без сохранения в БД."""
        if provider.lower() == "openrouter":
            return await validate_key(api_key)
        
        if base_url:
            from src.llm.openrouter import validate_generic_key
            return await validate_generic_key(api_key, base_url)
        
        return False

    @staticmethod
    @log_function
    async def get_active_connection() -> LLMConnection | None:
        """Возвращает активное подключение к LLM."""
        return await LLMConnection.filter(is_active=True).first()

    @staticmethod
    @log_function
    async def get_active_prompt(connection_id: int) -> LLMPrompt | None:
        """Возвращает активный промпт для указанного подключения."""
        return await LLMPrompt.filter(connection_id=connection_id, is_active=True).first()

    @staticmethod
    async def create_connection(
        name: str,
        provider: str,
        api_key: str,
        model_name: str,
        base_url: str | None = None,
        is_active: bool = False
    ) -> LLMConnection:
        """Создает новое подключение к LLM."""
        if is_active:
            # Деактивируем остальные, если это активно
            await LLMConnection.filter(is_active=True).update(is_active=False)
        
        return await LLMConnection.create(
            name=name,
            provider=provider,
            api_key=api_key,
            model_name=model_name,
            base_url=base_url,
            is_active=is_active
        )

    @staticmethod
    async def get_connection(connection_id: int) -> LLMConnection | None:
        """Возвращает подключение по ID."""
        return await LLMConnection.get_or_none(id=connection_id)

    @staticmethod
    async def update_connection(
        connection_id: int,
        name: str,
        provider: str,
        api_key: str,
        model_name: str,
        base_url: str | None = None
    ) -> LLMConnection | None:
        """Обновляет параметры подключения."""
        conn = await LLMConnection.get_or_none(id=connection_id)
        if conn:
            conn.name = name
            conn.provider = provider
            conn.api_key = api_key
            conn.model_name = model_name
            conn.base_url = base_url
            await conn.save()
            return conn
        return None

    @staticmethod
    async def delete_connection(connection_id: int) -> bool:
        """Удаляет подключение."""
        deleted_count = await LLMConnection.filter(id=connection_id).delete()
        return deleted_count > 0

    @staticmethod
    async def set_active_connection(connection_id: int) -> bool:
        """Устанавливает подключение как активное."""
        await LLMConnection.all().update(is_active=False)
        updated_count = await LLMConnection.filter(id=connection_id).update(is_active=True)
        return updated_count > 0

    @staticmethod
    async def create_prompt(
        connection_id: int,
        name: str,
        content: str,
        is_active: bool = False
    ) -> LLMPrompt:
        """Создает новый промпт для подключения."""
        if is_active:
            await LLMPrompt.filter(connection_id=connection_id, is_active=True).update(is_active=False)
        
        return await LLMPrompt.create(
            connection_id=connection_id,
            name=name,
            content=content,
            is_active=is_active
        )

    @staticmethod
    async def update_prompt(
        prompt_id: int,
        name: str,
        content: str
    ) -> LLMPrompt | None:
        """Обновляет существующий промпт."""
        prompt = await LLMPrompt.get_or_none(id=prompt_id)
        if prompt:
            prompt.name = name
            prompt.content = content
            await prompt.save()
            return prompt
        return None

    @staticmethod
    async def set_active_prompt(prompt_id: int) -> bool:
        """Устанавливает промпт как активный для его подключения."""
        prompt = await LLMPrompt.get_or_none(id=prompt_id)
        if not prompt:
            return False
        
        await LLMPrompt.filter(connection_id=prompt.connection_id).update(is_active=False)
        prompt.is_active = True
        await prompt.save()
        return True

    @staticmethod
    async def delete_prompt(prompt_id: int) -> bool:
        """Удаляет промпт."""
        deleted_count = await LLMPrompt.filter(id=prompt_id).delete()
        return deleted_count > 0

    @staticmethod
    async def list_connections() -> list[LLMConnection]:
        """Возвращает список всех подключений, отсортированных по ID."""
        return await LLMConnection.all().order_by("id")

    @staticmethod
    async def list_prompts(connection_id: int) -> list[LLMPrompt]:
        """Возвращает список промптов для подключения, отсортированных по ID."""
        return await LLMPrompt.filter(connection_id=connection_id).all().order_by("id")
