from tortoise.functions import Count

from src.database import ChatMessage
from src.logger import log_function


class HistoryService:
    """Сервис для работы с историей чатов."""

    @staticmethod
    @log_function
    async def add_message(chat_id: int, role: str, content: str) -> ChatMessage:
        """Добавляет сообщение в историю."""
        return await ChatMessage.create(chat_id=chat_id, role=role, content=content)

    @staticmethod
    @log_function
    async def get_last_messages(chat_id: int, limit: int = 10) -> list[dict[str, str]]:
        """Возвращает последние сообщения чата."""
        recent_messages = (
            await ChatMessage.filter(chat_id=chat_id)
            .order_by("-created_at")
            .limit(limit * 2)
        )
        # Sort back to chronological order
        recent_messages.sort(key=lambda x: x.created_at)
        return [{"role": m.role, "content": m.content} for m in recent_messages]

    @staticmethod
    @log_function
    async def clear_history(chat_id: int) -> None:
        """Очищает историю конкретного чата."""
        await ChatMessage.filter(chat_id=chat_id).delete()

    @staticmethod
    async def clear_all_history() -> None:
        """Очищает всю историю сообщений."""
        await ChatMessage.all().delete()

    @staticmethod
    async def get_stats() -> dict[str, int]:
        """Возвращает статистику по сообщениям."""
        total_messages = await ChatMessage.all().count()
        chats_count = await ChatMessage.all().distinct().values_list("chat_id", flat=True)
        return {"chats_count": len(chats_count), "total_messages": total_messages}

    @staticmethod
    async def list_chats() -> list[dict[str, int]]:
        """Возвращает список чатов с количеством сообщений."""
        stats = (
            await ChatMessage.annotate(message_count=Count("id"))
            .group_by("chat_id")
            .values("chat_id", "message_count")
        )
        return list(stats)

