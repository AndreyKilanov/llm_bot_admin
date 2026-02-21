import pytest
from unittest.mock import AsyncMock, patch
import httpx
from src.llm.client import LLMClient

@pytest.fixture
def mock_messages():
    return [{"role": "user", "content": "Hello"}]

@pytest.mark.asyncio
async def test_get_completion_empty_messages():
    with pytest.raises(ValueError, match="No messages to send"):
        await LLMClient.get_completion([], "key", "model", "url")

@pytest.mark.asyncio
async def test_get_completion_empty_base_url(mock_messages):
    with pytest.raises(ValueError, match="base_url is required"):
        await LLMClient.get_completion(mock_messages, "key", "model", "")

@pytest.mark.asyncio
@patch("src.llm.client.httpx.AsyncClient.post")
async def test_get_completion_success(mock_post, mock_messages):
    mock_post.return_value = AsyncMock(
        status_code=200,
        json=lambda: {"choices": [{"message": {"content": "Response"}}]}
    )
    
    result = await LLMClient.get_completion(mock_messages, "key", "model", "http://api.com/v1")
    
    assert result == "Response"
    mock_post.assert_awaited_once()

@pytest.mark.asyncio
@patch("src.llm.client.httpx.AsyncClient.post")
async def test_get_completion_no_choices(mock_post, mock_messages):
    mock_post.return_value = AsyncMock(
        status_code=200,
        json=lambda: {"choices": []}
    )
    
    with pytest.raises(ValueError, match="API returned no choices"):
        await LLMClient.get_completion(mock_messages, "key", "model", "http://api.com/v1")

@pytest.mark.asyncio
@patch("src.llm.client.httpx.AsyncClient.post")
async def test_get_completion_empty_content(mock_post, mock_messages):
    mock_post.return_value = AsyncMock(
        status_code=200,
        json=lambda: {"choices": [{"message": {"content": None}}]}
    )
    
    with pytest.raises(ValueError, match="API returned empty content"):
        await LLMClient.get_completion(mock_messages, "key", "model", "http://api.com/v1")

@pytest.mark.asyncio
@patch("src.llm.client.httpx.AsyncClient.post")
async def test_get_completion_status_not_200(mock_post, mock_messages):
    mock_post.return_value = AsyncMock(
        status_code=400,
        json=lambda: {"error": {"message": "Bad Request"}},
        text="Bad Request text"
    )
    
    with pytest.raises(ValueError, match="LLM API Error 400: Bad Request"):
        await LLMClient.get_completion(mock_messages, "key", "model", "http://api.com/v1")

@pytest.mark.asyncio
@patch("src.llm.client.asyncio.sleep")
@patch("src.llm.client.httpx.AsyncClient.post")
async def test_get_completion_retries(mock_post, mock_sleep, mock_messages):
    mock_post.side_effect = httpx.ConnectError("Connection failed")
    
    with pytest.raises(ValueError, match="Не удалось подключиться к LLM API после 3 попыток"):
        await LLMClient.get_completion(mock_messages, "key", "model", "http://api.com/v1")
        
    assert mock_post.await_count == 3
    assert mock_sleep.await_count == 2

@pytest.mark.asyncio
async def test_validate_key_empty_base_url():
    res = await LLMClient.validate_key("key", "")
    assert res is False

@pytest.mark.asyncio
@patch("src.llm.client.httpx.AsyncClient.get")
async def test_validate_key_success(mock_get):
    mock_get.return_value = AsyncMock(status_code=200)
    
    res = await LLMClient.validate_key("key", "http://api.com/v1")
    
    assert res is True
    mock_get.assert_awaited_once()

@pytest.mark.asyncio
@patch("src.llm.client.httpx.AsyncClient.get")
async def test_validate_key_failure(mock_get):
    mock_get.return_value = AsyncMock(status_code=401)
    
    res = await LLMClient.validate_key("key", "http://api.com/v1")
    
    assert res is False
    
@pytest.mark.asyncio
@patch("src.llm.client.httpx.AsyncClient.get")
async def test_validate_key_exception(mock_get):
    mock_get.side_effect = Exception("error")
    
    res = await LLMClient.validate_key("key", "http://api.com/v1")
    
    assert res is False
