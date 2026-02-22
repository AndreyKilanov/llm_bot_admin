import pytest
from datetime import datetime
from tortoise import Tortoise
from src.services.history_service import HistoryService
from src.database.models import ChatMessage, AllowedChat


@pytest.mark.asyncio
async def test_add_message():
    msg = await HistoryService.add_message(
        chat_id=1, role="user", content="hello", platform="telegram"
    )
    assert msg.content == "hello"
    assert msg.role == "user"

@pytest.mark.asyncio
async def test_add_message_with_title_new_chat():
    await HistoryService.add_message(
        chat_id=2, role="user", content="hello", title="Test Chat", nickname="TestUser"
    )
    chat = await AllowedChat.get(chat_id=2)
    assert chat.title == "Test Chat (TestUser)"

@pytest.mark.asyncio
async def test_add_message_with_title_existing_chat():
    await AllowedChat.create(chat_id=3, platform="telegram", title="Old Title")
    await HistoryService.add_message(
        chat_id=3, role="user", content="hello", title="New Title", chat_type="group"
    )
    chat = await AllowedChat.get(chat_id=3)
    assert chat.title == "New Title"

@pytest.mark.asyncio
async def test_get_last_messages():
    await HistoryService.add_message(chat_id=4, role="user", content="msg1")
    await HistoryService.add_message(chat_id=4, role="assistant", content="msg2")
    
    msgs = await HistoryService.get_last_messages(chat_id=4, limit=1)
    # The limit is multiplied by 2 in the method (limit*2) so it gets 2 messages
    assert len(msgs) == 2
    assert msgs[0]["content"] == "msg1"
    assert msgs[1]["content"] == "msg2"

@pytest.mark.asyncio
async def test_clear_history():
    await HistoryService.add_message(chat_id=5, role="user", content="msg")
    await HistoryService.add_message(chat_id=6, role="user", content="msg2")
    
    await HistoryService.clear_history(chat_id=5)
    
    assert await ChatMessage.filter(chat_id=5).count() == 0
    assert await ChatMessage.filter(chat_id=6).count() == 1

@pytest.mark.asyncio
async def test_clear_all_history():
    await HistoryService.add_message(chat_id=7, role="user", content="msg")
    await HistoryService.clear_all_history()
    assert await ChatMessage.all().count() == 0

@pytest.mark.asyncio
async def test_get_stats():
    await HistoryService.add_message(chat_id=8, role="user", content="u1", platform="telegram")
    await HistoryService.add_message(chat_id=8, role="assistant", content="a1", platform="telegram")
    await HistoryService.add_message(chat_id=9, role="user", content="u2", platform="discord")
    
    stats = await HistoryService.get_stats()
    assert stats["chats_count"] == 2
    assert stats["total_messages"] == 3
    assert stats["telegram_messages"] == 2
    assert stats["discord_messages"] == 1
    assert stats["assistant_messages"] == 1
    assert stats["user_messages"] == 2
    assert stats["messages_24h"] == 3
    assert stats["active_chats_24h"] == 2

@pytest.mark.asyncio
async def test_list_chats():
    await HistoryService.add_message(chat_id=10, role="user", content="u", platform="telegram", chat_type="private")
    chats = await HistoryService.list_chats()
    assert len(chats) == 1
    assert chats[0]["chat_id"] == 10
    assert chats[0]["message_count"] == 1
    assert chats[0]["platform"] == "telegram"
    assert chats[0]["chat_type"] == "private"
