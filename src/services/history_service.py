from datetime import datetime, timedelta, timezone
from typing import Any

from tortoise.functions import Count, Max

from src.database import ChatMessage
from src.logger import log_function
from src.database.models import AllowedChat


class HistoryService:
    """Сервис для работы с историей чатов."""

    @staticmethod
    @log_function
    async def add_message(
        chat_id: int, 
        role: str, 
        content: str, 
        platform: str = "telegram", 
        chat_type: str = "private",
        title: str = None,
        nickname: str = None
    ) -> ChatMessage:
        """Добавляет сообщение в историю и обновляет метаданные чата."""
        if title:
            if chat_type == "private" and nickname:
                if f"({nickname})" not in title:
                    title = f"{title} ({nickname})"

            chat_info = await AllowedChat.get_or_none(chat_id=chat_id, platform=platform)
            if chat_info:
                if chat_info.title != title:
                    chat_info.title = title
                    await chat_info.save()
            else:
                await AllowedChat.create(
                    chat_id=chat_id,
                    platform=platform,
                    title=title,
                    is_active=False
                )
        
        return await ChatMessage.create(
            chat_id=chat_id, 
            role=role, 
            content=content, 
            platform=platform, 
            chat_type=chat_type,
            nickname=nickname
        )

    @staticmethod
    @log_function
    async def get_last_messages(chat_id: int, platform: str = "telegram", limit: int = 10) -> list[dict[str, str]]:
        """Возвращает последние сообщения чата."""
        recent_messages = (
            await ChatMessage.filter(chat_id=chat_id, platform=platform)
            .order_by("-created_at")
            .limit(limit * 2)
        )
        recent_messages.sort(key=lambda x: x.created_at)
        return [{"role": m.role, "content": m.content, "nickname": m.nickname} for m in recent_messages]

    @staticmethod
    @log_function
    async def clear_history(chat_id: int, platform: str = "telegram") -> None:
        """Очищает историю конкретного чата."""
        await ChatMessage.filter(chat_id=chat_id, platform=platform).delete()

    @staticmethod
    async def clear_all_history() -> None:
        """Очищает всю историю сообщений."""
        await ChatMessage.all().delete()

    @staticmethod
    async def get_stats() -> dict[str, Any]:
        """Возвращает статистику по сообщениям."""
        now = datetime.now(timezone.utc)
        last_24h = now - timedelta(days=1)
        total_messages = await ChatMessage.all().count()
        chats_count = len(await ChatMessage.all().distinct().values_list("chat_id", flat=True))
        tg_stats = await ChatMessage.filter(platform="telegram").count()
        dc_stats = await ChatMessage.filter(platform="discord").count()
        messages_24h = await ChatMessage.filter(created_at__gte=last_24h).count()
        active_chats_24h = len(await ChatMessage.filter(created_at__gte=last_24h).distinct().values_list("chat_id", flat=True))
        assistant_messages = await ChatMessage.filter(role="assistant").count()
        user_messages = await ChatMessage.filter(role="user").count()

        return {
            "chats_count": chats_count, 
            "total_messages": total_messages,
            "telegram_messages": tg_stats,
            "discord_messages": dc_stats,
            "messages_24h": messages_24h,
            "active_chats_24h": active_chats_24h,
            "assistant_messages": assistant_messages,
            "user_messages": user_messages
        }

    @staticmethod
    async def list_chats() -> list[dict[str, Any]]:
        """Возвращает список чатов с количеством сообщений и метаданными."""
        stats = (
            await ChatMessage.annotate(
                message_count=Count("id"),
                last_message_at=Max("created_at")
            )
            .group_by("chat_id", "platform", "chat_type")
            .values("chat_id", "platform", "chat_type", "message_count", "last_message_at")
        )
        return list(stats)
