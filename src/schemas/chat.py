from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ChatMessagePayload(BaseModel):
    """Модель сообщения для передачи в LLM и между сервисами."""
    role: str
    content: str
    nickname: str | None = None

    model_config = ConfigDict(extra="ignore")


class ChatStats(BaseModel):
    """Сводная статистика по истории сообщений."""
    chats_count: int
    total_messages: int
    telegram_messages: int
    discord_messages: int
    messages_24h: int
    active_chats_24h: int
    assistant_messages: int
    user_messages: int


class ChatInfo(BaseModel):
    """Информация о конкретном чате."""
    chat_id: int | str
    platform: str
    chat_type: str
    message_count: int
    last_message_at: datetime | None
