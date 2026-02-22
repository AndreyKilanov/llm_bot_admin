import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from aiogram.types import Message, User, Chat
from aiogram.enums import ChatType

from src.bot.telegram.handlers import (
    cmd_start, cmd_clear, cmd_help, cmd_prompt, cmd_set_prompt, cmd_cancel, on_text, _waiting_prompt
)
from src.exceptions import ConfigurationError

@pytest.fixture(autouse=True)
def clean_waiting_prompt():
    _waiting_prompt.clear()
    yield
    _waiting_prompt.clear()


@pytest.mark.asyncio
async def test_cmd_start(mock_tg_message):
    await cmd_start(mock_tg_message)
    mock_tg_message.answer.assert_called_once()
    assert "Привет" in mock_tg_message.answer.call_args[0][0]


@pytest.mark.asyncio
@patch("src.bot.telegram.handlers.HistoryService.clear_history")
async def test_cmd_clear(mock_clear, mock_tg_message):
    await cmd_clear(mock_tg_message)
    mock_clear.assert_called_once_with(456, platform="telegram")
    mock_tg_message.answer.assert_called_once_with("История очищена.")


@pytest.mark.asyncio
async def test_cmd_help(mock_tg_message):
    await cmd_help(mock_tg_message)
    mock_tg_message.answer.assert_called_once()
    assert "LLM Бот-ассистент" in mock_tg_message.answer.call_args[0][0]


@pytest.mark.asyncio
@patch("src.bot.telegram.handlers.SettingsService.get_system_prompt")
async def test_cmd_prompt(mock_get_prompt, mock_tg_message):
    mock_get_prompt.return_value = "You are a bot"
    await cmd_prompt(mock_tg_message)
    mock_tg_message.answer.assert_called_once()
    assert "You are a bot" in mock_tg_message.answer.call_args[0][0]


@pytest.mark.asyncio
@patch("src.bot.telegram.handlers._get_admin_ids")
async def test_cmd_set_prompt_no_access(mock_admins, mock_tg_message):
    mock_admins.return_value = {999}  # Not 123
    await cmd_set_prompt(mock_tg_message)
    mock_tg_message.answer.assert_called_once_with("Нет доступа.")
    assert 123 not in _waiting_prompt


@pytest.mark.asyncio
@patch("src.bot.telegram.handlers._get_admin_ids")
async def test_cmd_set_prompt_with_access(mock_admins, mock_tg_message):
    mock_admins.return_value = {123}
    await cmd_set_prompt(mock_tg_message)
    mock_tg_message.answer.assert_called_once()
    assert "Отправьте новый промпт" in mock_tg_message.answer.call_args[0][0]
    assert 123 in _waiting_prompt


@pytest.mark.asyncio
async def test_cmd_cancel(mock_tg_message):
    _waiting_prompt.add(123)
    await cmd_cancel(mock_tg_message)
    mock_tg_message.answer.assert_called_once_with("Отменено.")
    assert 123 not in _waiting_prompt


@pytest.mark.asyncio
@patch("src.bot.telegram.handlers.SettingsService.set_system_prompt")
async def test_on_text_waiting_prompt(mock_set_prompt, mock_tg_message):
    _waiting_prompt.add(123)
    mock_tg_message.text = "New prompt"
    await on_text(mock_tg_message)
    
    mock_set_prompt.assert_called_once_with("New prompt")
    mock_tg_message.answer.assert_called_once_with("Промпт обновлён.")
    assert 123 not in _waiting_prompt


@pytest.mark.asyncio
@patch("src.bot.telegram.handlers.HistoryService.add_message")
@patch("src.bot.telegram.handlers.HistoryService.get_last_messages")
@patch("src.bot.telegram.handlers.LLMService.generate_response")
async def test_on_text_private_chat(mock_gen, mock_get_last, mock_add, mock_tg_message):
    mock_tg_message.text = "Hello there"
    mock_get_last.return_value = [{"role": "user", "content": "Hello there"}]
    mock_gen.return_value = "Hi human!"
    
    await on_text(mock_tg_message)
    
    assert mock_add.call_count == 2
    mock_gen.assert_called_once()
    mock_tg_message.answer.assert_called_once_with("Hi human!")


@pytest.mark.asyncio
@patch("src.bot.telegram.handlers.LLMService.generate_response")
async def test_on_text_group_no_mention(mock_gen, mock_tg_message):
    mock_tg_message.chat.type = ChatType.GROUP
    mock_tg_message.text = "Just talking"
    
    await on_text(mock_tg_message)
    
    # Should ignore group messages unless mentioned or replied
    mock_gen.assert_not_called()


@pytest.mark.asyncio
@patch("src.bot.telegram.handlers.HistoryService.add_message")
@patch("src.bot.telegram.handlers.HistoryService.get_last_messages")
@patch("src.bot.telegram.handlers.LLMService.generate_response")
async def test_on_text_group_with_mention(mock_gen, mock_get_last, mock_add, mock_tg_message):
    mock_tg_message.chat.type = ChatType.GROUP
    mock_tg_message.text = "Hey @test_bot how are you?"
    mock_get_last.return_value = [{"role": "user", "content": "how are you?"}]
    mock_gen.return_value = "I am good!"
    
    await on_text(mock_tg_message)
    
    mock_gen.assert_called_once()
    # Check that mention was stripped
    first_add_call = mock_add.call_args_list[0]
    assert first_add_call[0][2] == "hey  how are you?"
    
    mock_tg_message.answer.assert_called_once_with("I am good!")


@pytest.mark.asyncio
@patch("src.bot.telegram.handlers.HistoryService.add_message")
@patch("src.bot.telegram.handlers.HistoryService.get_last_messages")
@patch("src.bot.telegram.handlers.LLMService.generate_response")
async def test_on_text_llm_error(mock_gen, mock_get_last, mock_add, mock_tg_message):
    mock_tg_message.text = "Hello"
    mock_gen.side_effect = ConfigurationError("API key invalid")
    
    await on_text(mock_tg_message)
    
    mock_tg_message.answer.assert_called_once()
    assert "Ошибка конфигурации" in mock_tg_message.answer.call_args[0][0]
    # Response was not saved to history
    assert mock_add.call_count == 1
