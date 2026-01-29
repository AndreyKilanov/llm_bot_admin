import httpx

OPENROUTER_URL = "https://openrouter.ai/api/v1"


async def get_completion(
    messages: list[dict[str, str]],
    api_key: str,
    model: str,
    base_url: str | None = None,
) -> str:
    """Выполняет запрос к LLM API.

    Args:
        messages: Список сообщений в формате [{'role': '...', 'content': '...'}]
        api_key: Ключ API
        model: Название модели
        base_url: Базовый URL API (по умолчанию OpenRouter)

    Returns:
        Текст ответа ассистента.
    """
    filtered_messages = [m for m in messages if m.get("content")]
    if not filtered_messages:
        raise ValueError("No messages to send")

    url = base_url or OPENROUTER_URL
    url = url.rstrip("/")
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
        raise ValueError(f"OpenRouter API Error {resp.status_code}: {error_msg}")

    data = resp.json()
    choices = data.get("choices")
    if not choices:
        raise ValueError("API returned no choices")

    content = choices[0].get("message", {}).get("content")
    if content is None:
        raise ValueError("API returned empty content")

    return content.strip() if isinstance(content, str) else str(content)


async def validate_key(api_key: str) -> bool:
    """Проверяет валидность API ключа OpenRouter.

    Args:
        api_key: Ключ API

    Returns:
        True если ключ валиден, иначе False.
    """
    url = f"{OPENROUTER_URL}/auth/key"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            return resp.status_code == 200
    except Exception:
        return False

async def validate_generic_key(api_key: str, base_url: str) -> bool:
    """Универсальная проверка ключа через эндпоинт /models.
    
    Подходит для большинства OpenAI-совместимых провайдеров.
    """
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
            # 200 - успех, 401/403 - невалидный ключ
            return resp.status_code == 200
    except Exception:
        return False
