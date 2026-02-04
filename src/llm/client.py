import httpx


class LLMClient:
    """Универсальный клиент для работы с LLM через OpenAI-совместимый API.

    Поддерживает OpenRouter, Groq, OpenAI и другие совместимые провайдеры.
    Требует явного указания base_url — дефолтов нет.
    """

    @classmethod
    async def get_completion(
            cls,
            messages: list[dict[str, str]],
            api_key: str,
            model: str,
            base_url: str,
    ) -> str:
        """Выполняет запрос к LLM API.

        Args:
            messages: Список сообщений в формате [{'role': '...', 'content': '...'}]
            api_key: Ключ API
            model: Название модели
            base_url: Базовый URL API (обязателен)

        Returns:
            Текст ответа ассистента.
        """
        filtered_messages = [
            {"role": m["role"], "content": m["content"]} 
            for m in messages if m.get("content")
        ]
        if not filtered_messages:
            raise ValueError("No messages to send")

        url = base_url.rstrip("/")
        if url.endswith("/chat/completions"):
            pass
        elif url.endswith("/v1"):
            url += "/chat/completions"
        else:
            url += "/v1/chat/completions"

        payload = {
            "model": model,
            "messages": filtered_messages,
            "max_tokens": 4096,
            "temperature": 0.7,
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            # OpenRouter-specific headers
            "HTTP-Referer": "https://github.com/google/llm_bot",
            "X-Title": "LLM Bot",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload, headers=headers)

        if resp.status_code != 200:
            try:
                error_data = resp.json()
                error_msg = error_data.get("error", {}).get("message", resp.text)
            except Exception:
                error_msg = resp.text
            raise ValueError(f"LLM API Error {resp.status_code}: {error_msg}")

        data = resp.json()
        choices = data.get("choices")
        if not choices:
            raise ValueError("API returned no choices")

        content = choices[0].get("message", {}).get("content")
        if content is None:
            raise ValueError("API returned empty content")

        return content.strip() if isinstance(content, str) else str(content)

    @classmethod
    async def validate_key(cls, api_key: str, base_url: str) -> bool:
        """Проверяет валидность API ключа через универсальный эндпоинт /models.

        Args:
            api_key: Ключ API
            base_url: Базовый URL API (обязателен)

        Returns:
            True если ключ валиден, иначе False.
        """
        return await cls._validate_generic_key(api_key, base_url)

    @staticmethod
    async def _validate_generic_key(api_key: str, base_url: str) -> bool:
        """Внутренний метод для универсальной проверки ключа через эндпоинт /models."""
        url = base_url.rstrip("/")

        if url.endswith("/chat/completions"):
            url = url[:-17].rstrip("/")

        if not url.endswith("/v1"):
            url += "/v1"
        url += "/models"

        headers = {"Authorization": f"Bearer {api_key}"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=headers)
                return resp.status_code == 200
        except Exception:
            return False
