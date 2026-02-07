from config import settings
from src.database.models import LLMConnection, LLMPrompt
from src.llm import LLMClient
from src.logger import log_function


class LLMService:
    """Сервис для управления подключениями к LLM и их промптами."""

    PROVIDER_DEFAULT_URLS = settings.PROVIDER_DEFAULT_URLS

    @staticmethod
    @log_function
    async def check_connection(connection_id: int) -> bool:
        """Проверяет работоспособность подключения к LLM по его ID.

        Метод извлекает подключение из базы данных и выполняет валидацию API-ключа.
        Если base_url не указан, используется дефолтный URL для известных провайдеров.
        Если провайдер неизвестен и base_url отсутствует — проверка невозможна.

        Args:
            connection_id: Уникальный идентификатор подключения к LLM.

        Returns:
            True, если подключение успешно прошло валидацию; иначе False.
        """
        conn = await LLMConnection.get_or_none(id=connection_id)
        if not conn:
            return False

        base_url = conn.base_url
        if not base_url:
            provider_info = LLMService.PROVIDER_DEFAULT_URLS.get(conn.provider.lower())
            if isinstance(provider_info, dict):
                base_url = provider_info.get("url")
            else:
                base_url = provider_info  # Fallback for old simple strings if they somehow exist

        if not base_url:
            from src.logger import get_logger
            get_logger("llm_service").warning(
                f"Connection check failed: no base_url and no default for provider '{conn.provider}'"
            )
            return False

        return await LLMClient.validate_key(conn.api_key, base_url)

    @staticmethod
    async def check_temporary_connection(provider: str, api_key: str, base_url: str | None = None) -> bool:
        """Проверяет работоспособность временного подключения без сохранения в БД.

        Используется для предварительной проверки корректности параметров подключения
        перед их сохранением. Поддерживает fallback для известных провайдеров.

        Args:
            provider: Название провайдера LLM (например, 'openrouter').
            api_key: API-ключ для аутентификации.
            base_url: Опциональный URL endpoint'а. Если не указан — используется дефолт для провайдера.

        Returns:
            True, если ключ действителен и подключение возможно; иначе False.
        """
        if not base_url:
            provider_info = LLMService.PROVIDER_DEFAULT_URLS.get(provider.lower())
            if isinstance(provider_info, dict):
                base_url = provider_info.get("url")
            else:
                base_url = provider_info

        if not base_url:
            return False

        return await LLMClient.validate_key(api_key, base_url)

    @staticmethod
    @log_function
    async def get_active_connection() -> LLMConnection | None:
        """Возвращает активное (is_active=True) подключение к LLM.

        В системе может быть только одно активное подключение. Если таких нет,
        возвращается None.

        Returns:
            Экземпляр LLMConnection, если активное подключение существует; иначе None.
        """
        return await LLMConnection.filter(is_active=True).first()

    @staticmethod
    @log_function
    async def get_active_prompt(connection_id: int) -> LLMPrompt | None:
        """Возвращает активный промпт для указанного подключения.

        Каждое подключение может иметь ровно один активный промпт. Если такового нет,
        возвращается None.

        Args:
            connection_id: ID подключения, для которого ищется активный промпт.

        Returns:
            Экземпляр LLMPrompt, если активный промпт найден; иначе None.
        """
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
        """Создаёт новое подключение к LLM и сохраняет его в базе данных.

        Если флаг is_active=True, все остальные подключения автоматически
        деактивируются.

        Args:
            name: Человекочитаемое название подключения.
            provider: Провайдер LLM (например, 'openai', 'openrouter').
            api_key: Секретный API-ключ.
            model_name: Название модели (например, 'gpt-4o').
            base_url: Опциональный кастомный endpoint (для self-hosted или альтернативных API).
            is_active: Следует ли сделать это подключение активным.

        Returns:
            Созданный экземпляр LLMConnection.
        """
        if is_active:
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
        """Получает подключение по его уникальному идентификатору.

        Args:
            connection_id: ID подключения в базе данных.

        Returns:
            Экземпляр LLMConnection, если найден; иначе None.
        """
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
        """Обновляет параметры существующего подключения.

        Args:
            connection_id: ID обновляемого подключения.
            name: Новое название.
            provider: Новый провайдер.
            api_key: Новый API-ключ.
            model_name: Новое название модели.
            base_url: Новый (или обновлённый) base URL.

        Returns:
            Обновлённый экземпляр LLMConnection, если подключение существует;
            иначе None.
        """
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
        """Удаляет подключение из базы данных по ID.

        Args:
            connection_id: ID удаляемого подключения.

        Returns:
            True, если подключение было успешно удалено; иначе False.
        """
        deleted_count = await LLMConnection.filter(id=connection_id).delete()
        return deleted_count > 0

    @staticmethod
    async def set_active_connection(connection_id: int) -> bool:
        """Делает указанное подключение активным.

        Все остальные подключения автоматически деактивируются.

        Args:
            connection_id: ID подключения, которое нужно активировать.

        Returns:
            True, если подключение найдено и активировано; иначе False.
        """
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
        """Создаёт новый промпт, привязанный к указанному подключению.

        Если is_active=True, предыдущий активный промпт для этого подключения
        деактивируется.

        Args:
            connection_id: ID подключения, к которому привязывается промпт.
            name: Название промпта.
            content: Текст промпта.
            is_active: Следует ли сделать этот промпт активным.

        Returns:
            Созданный экземпляр LLMPrompt.
        """
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
        """Обновляет существующий промпт по его ID.

        Args:
            prompt_id: ID обновляемого промпта.
            name: Новое название.
            content: Новое содержимое промпта.

        Returns:
            Обновлённый экземпляр LLMPrompt, если промпт существует; иначе None.
        """
        prompt = await LLMPrompt.get_or_none(id=prompt_id)
        if prompt:
            prompt.name = name
            prompt.content = content
            await prompt.save()
            return prompt
        return None

    @staticmethod
    async def set_active_prompt(prompt_id: int) -> bool:
        """Активирует указанный промпт для его подключения.

        Все другие промпты, привязанные к тому же подключению, деактивируются.

        Args:
            prompt_id: ID промпта, который нужно сделать активным.

        Returns:
            True, если промпт найден и успешно активирован; иначе False.
        """
        prompt = await LLMPrompt.get_or_none(id=prompt_id)
        if not prompt:
            return False

        await LLMPrompt.filter(connection_id=prompt.connection_id).update(is_active=False)
        prompt.is_active = True
        await prompt.save()
        return True

    @staticmethod
    async def delete_prompt(prompt_id: int) -> bool:
        """Удаляет промпт по его ID.

        Args:
            prompt_id: ID удаляемого промпта.

        Returns:
            True, если промпт был успешно удалён; иначе False.
        """
        deleted_count = await LLMPrompt.filter(id=prompt_id).delete()
        return deleted_count > 0

    @staticmethod
    async def list_connections() -> list[LLMConnection]:
        """Возвращает список всех подключений, отсортированных по возрастанию ID.

        Returns:
            Список экземпляров LLMConnection.
        """
        return await LLMConnection.all().order_by("id")

    @staticmethod
    async def list_prompts(connection_id: int) -> list[LLMPrompt]:
        """Возвращает список всех промптов для указанного подключения.

        Результат отсортирован по возрастанию ID.

        Args:
            connection_id: ID подключения, для которого запрашиваются промпты.

        Returns:
            Список экземпляров LLMPrompt.
        """
        return await LLMPrompt.filter(connection_id=connection_id).all().order_by("id")

    @staticmethod
    @log_function
    async def get_system_prompt_content() -> str:
        """Возвращает актуальный системный промпт.

        Сначала проверяет наличие активного промпта у активного подключения.
        Если нет активного подключения или промпта — возвращает глобальный промпт из настроек.

        Returns:
            Текст системного промпта.
        """
        from src.services.settings_service import SettingsService

        active_conn = await LLMService.get_active_connection()
        if active_conn:
            db_prompt = await LLMService.get_active_prompt(active_conn.id)
            if db_prompt:
                return db_prompt.content

        return await SettingsService.get_system_prompt()

    @staticmethod
    @log_function
    async def generate_response(messages: list[dict], system_prompt: str | None = None) -> str:
        """Генерирует ответ от LLM, используя активное подключение или настройки по умолчанию.

        Args:
            messages: Список предыдущих сообщений диалога (без системного промпта).
            system_prompt: Опциональный системный промпт. Если не передан — будет получен автоматически.

        Returns:
            Текст ответа от модели.
        """
        if system_prompt is None:
            system_prompt = await LLMService.get_system_prompt_content()

        active_conn = await LLMService.get_active_connection()

        if not active_conn:
            raise ValueError("Отсутствует активное соединение с LLM API")

        api_key = active_conn.api_key
        model = active_conn.model_name
        base_url = active_conn.base_url
        provider = active_conn.provider

        # Если base_url не указан, пытаемся взять дефолтный для провайдера
        if not base_url:
            provider_info = LLMService.PROVIDER_DEFAULT_URLS.get(provider.lower())
            if isinstance(provider_info, dict):
                base_url = provider_info.get("url")
            else:
                base_url = provider_info

        if not base_url:
            raise ValueError(f"Base URL not found for provider '{provider}'")

        full_messages = [{"role": "system", "content": system_prompt}] + messages

        return await LLMClient.get_completion(
            messages=full_messages,
            api_key=api_key,
            model=model,
            base_url=base_url
        )
