import pytest
from unittest.mock import AsyncMock, patch

from src.database.models import LLMConnection, LLMPrompt
from src.services.llm_service import LLMService
from src.exceptions import ConfigurationError

@pytest.fixture(autouse=True)
async def clear_db():
    await LLMPrompt.all().delete()
    await LLMConnection.all().delete()
    yield

@pytest.fixture
def mock_llm_client():
    with patch("src.services.llm_service.LLMClient") as mock:
        mock.validate_key = AsyncMock(return_value=True)
        mock.get_completion = AsyncMock(return_value="Mocked response")
        yield mock


@pytest.mark.asyncio
async def test_create_and_get_connection():
    conn = await LLMService.create_connection(
        name="Test", provider="openai", api_key="test_key", model_name="gpt-4o"
    )
    fetched = await LLMService.get_connection(conn.id)
    assert fetched is not None
    assert fetched.name == "Test"
    assert fetched.model_name == "gpt-4o"


@pytest.mark.asyncio
async def test_create_connection_makes_others_inactive():
    conn1 = await LLMService.create_connection(
        name="Test 1", provider="openai", api_key="k1", model_name="m1", is_active=True
    )
    conn2 = await LLMService.create_connection(
        name="Test 2", provider="openai", api_key="k2", model_name="m2", is_active=True
    )
    
    fetched1 = await LLMService.get_connection(conn1.id)
    fetched2 = await LLMService.get_connection(conn2.id)
    
    assert fetched1.is_active is False
    assert fetched2.is_active is True


@pytest.mark.asyncio
async def test_update_connection():
    conn = await LLMService.create_connection(
        name="Test", provider="openai", api_key="test_key", model_name="gpt-4o"
    )
    updated = await LLMService.update_connection(
        connection_id=conn.id,
        name="Updated",
        provider="openrouter",
        api_key="new_key",
        model_name="claude-3",
        base_url="https://new.url"
    )
    assert updated.name == "Updated"
    assert updated.provider == "openrouter"
    assert updated.base_url == "https://new.url"


@pytest.mark.asyncio
async def test_delete_connection():
    conn = await LLMService.create_connection(
        name="Test", provider="openai", api_key="test_key", model_name="gpt-4o"
    )
    assert await LLMService.delete_connection(conn.id) is True
    assert await LLMService.get_connection(conn.id) is None
    assert await LLMService.delete_connection(9999) is False


@pytest.mark.asyncio
async def test_set_deactivate_active_connection():
    conn1 = await LLMService.create_connection(
        name="Test 1", provider="openai", api_key="k1", model_name="m1", is_active=False
    )
    conn2 = await LLMService.create_connection(
        name="Test 2", provider="openai", api_key="k2", model_name="m2", is_active=False
    )
    
    assert await LLMService.set_active_connection(conn1.id) is True
    assert (await LLMService.get_connection(conn1.id)).is_active is True
    assert (await LLMService.get_connection(conn2.id)).is_active is False
    
    assert await LLMService.set_active_connection(conn2.id) is True
    assert (await LLMService.get_connection(conn1.id)).is_active is False
    assert (await LLMService.get_connection(conn2.id)).is_active is True

    assert await LLMService.deactivate_connection(conn2.id) is True
    assert (await LLMService.get_connection(conn2.id)).is_active is False

@pytest.mark.asyncio
async def test_create_and_update_prompt():
    conn = await LLMService.create_connection(
        name="Test", provider="openai", api_key="k", model_name="m"
    )
    prompt = await LLMService.create_prompt(conn.id, "Prompt 1", "Sys prompt", True)
    
    assert prompt.name == "Prompt 1"
    assert prompt.is_active is True
    
    updated = await LLMService.update_prompt(prompt.id, "Updated", "New sys prompt")
    assert updated.name == "Updated"
    assert updated.content == "New sys prompt"

    assert await LLMService.delete_prompt(prompt.id) is True
    assert await LLMService.delete_prompt(prompt.id) is False

@pytest.mark.asyncio
async def test_set_active_prompt():
    conn = await LLMService.create_connection(
        name="Test", provider="openai", api_key="k", model_name="m"
    )
    p1 = await LLMService.create_prompt(conn.id, "P1", "C1", is_active=True)
    p2 = await LLMService.create_prompt(conn.id, "P2", "C2", is_active=False)
    
    assert await LLMService.set_active_prompt(p2.id) is True
    
    # Active state should switch
    db_p1 = await LLMPrompt.get(id=p1.id)
    db_p2 = await LLMPrompt.get(id=p2.id)
    assert db_p1.is_active is False
    assert db_p2.is_active is True

    assert await LLMService.deactivate_prompt(p2.id) is True
    assert (await LLMPrompt.get(id=p2.id)).is_active is False


@pytest.mark.asyncio
async def test_get_active_prompt_and_connection():
    conn = await LLMService.create_connection(
        name="C1", provider="openai", api_key="k", model_name="m", is_active=True
    )
    p = await LLMService.create_prompt(conn.id, "P1", "C", is_active=True)
    
    active_conn = await LLMService.get_active_connection()
    assert active_conn.id == conn.id
    
    active_p = await LLMService.get_active_prompt(conn.id)
    assert active_p.id == p.id

@pytest.mark.asyncio
async def test_list_data():
    conn = await LLMService.create_connection("C1", "openai", "k", "m")
    await LLMService.create_prompt(conn.id, "P1", "C")
    
    conns = await LLMService.list_connections()
    assert len(conns) == 1
    
    prompts = await LLMService.list_prompts(conn.id)
    assert len(prompts) == 1


@pytest.mark.asyncio
async def test_check_connection_valid(mock_llm_client):
    conn = await LLMService.create_connection(
        name="Test", provider="openai", api_key="test_key", model_name="gpt-4o"
    )
    result = await LLMService.check_connection(conn.id)
    
    assert result is True
    mock_llm_client.validate_key.assert_called_once()
    # base url from provider default expected
    provider_url = LLMService.PROVIDER_DEFAULT_URLS.get('openai')
    if isinstance(provider_url, dict):
        provider_url = provider_url.get("url")
    mock_llm_client.validate_key.assert_called_with("test_key", provider_url)

@pytest.mark.asyncio
async def test_check_connection_invalid_no_conn(mock_llm_client):
    assert await LLMService.check_connection(9999) is False

@pytest.mark.asyncio
async def test_check_connection_no_base_url(mock_llm_client):
    conn = await LLMService.create_connection(
        name="Test", provider="unknown_provider", api_key="test_key", model_name="gpt-4o"
    )
    assert await LLMService.check_connection(conn.id) is False


@pytest.mark.asyncio
async def test_check_temporary_connection(mock_llm_client):
    res = await LLMService.check_temporary_connection("openai", "key")
    assert res is True
    res2 = await LLMService.check_temporary_connection("unknown_provider", "key")
    assert res2 is False


@pytest.mark.asyncio
async def test_get_system_prompt_content_from_db():
    conn = await LLMService.create_connection("C1", "openai", "k", "m", is_active=True)
    await LLMService.create_prompt(conn.id, "P1", "System Override!", is_active=True)
    
    content = await LLMService.get_system_prompt_content()
    assert content == "System Override!"


@pytest.mark.asyncio
@patch("src.services.settings_service.SettingsService.get_system_prompt", new_callable=AsyncMock)
async def test_get_system_prompt_content_fallback(mock_get_system_prompt):
    mock_get_system_prompt.return_value = "Fallback default"
    # No active connection
    content = await LLMService.get_system_prompt_content()
    assert content == "Fallback default"

@pytest.mark.asyncio
async def test_generate_response_success(mock_llm_client):
    await LLMService.create_connection("C1", "openai", "k", "m", is_active=True)
    
    resp = await LLMService.generate_response([{"role": "user", "content": "hi"}], system_prompt="Sys")
    assert resp == "Mocked response"
    
    # Assert get_completion was called properly
    mock_llm_client.get_completion.assert_called_once()
    kwargs = mock_llm_client.get_completion.call_args.kwargs
    assert kwargs["messages"] == [{"role": "system", "content": "Sys"}, {"role": "user", "content": "hi"}]
    assert kwargs["api_key"] == "k"
    assert kwargs["model"] == "m"

@pytest.mark.asyncio
async def test_generate_response_no_active_connection():
    with pytest.raises(ConfigurationError, match="Отсутствует активное соединение"):
        await LLMService.generate_response([{"role": "user", "content": "hi"}])

@pytest.mark.asyncio
async def test_generate_response_unknown_provider_no_base_url(mock_llm_client):
    await LLMService.create_connection("C1", "unknown", "k", "m", is_active=True)
    with pytest.raises(ConfigurationError, match="Base URL not found"):
        await LLMService.generate_response([{"role": "user", "content": "hi"}])
