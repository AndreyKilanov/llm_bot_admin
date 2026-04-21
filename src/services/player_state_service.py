import json
import logging
from typing import Optional, Tuple
from src.database import Setting

logger = logging.getLogger("src.services.player_state_service")

class PlayerStateService:
    """Сервис для управления персистентным состоянием плеера.
    
    Использует таблицу Settings для хранения ID последнего сообщения плеера 
    для каждой гильдии (сервера).
    """

    @staticmethod
    async def save_player_msg(guild_id: int, channel_id: int, message_id: int) -> None:
        """Сохранить информацию о сообщении плеера в БД."""
        key = f"discord_player_msg_{guild_id}"
        data = json.dumps({"channel_id": channel_id, "message_id": message_id})
        await Setting.update_or_create(defaults={"value": data}, key=key)
        logger.debug("Состояние плеера сохранено для guild %d: %s", guild_id, data)

    @staticmethod
    async def get_player_msg(guild_id: int) -> Optional[Tuple[int, int]]:
        """Получить ID канала и сообщения плеера для гильдии."""
        key = f"discord_player_msg_{guild_id}"
        setting = await Setting.get_or_none(key=key)
        if setting:
            try:
                data = json.loads(setting.value)
                return data["channel_id"], data["message_id"]
            except (json.JSONDecodeError, KeyError):
                return None
        return None

    @staticmethod
    async def clear_player_msg(guild_id: int) -> None:
        """Удалить запись о сообщении плеера из БД."""
        key = f"discord_player_msg_{guild_id}"
        setting = await Setting.get_or_none(key=key)
        if setting:
            await setting.delete()
            logger.debug("Состояние плеера удалено из БД для guild %d", guild_id)

    @staticmethod
    async def get_all_player_states() -> list[tuple[int, int, int]]:
        """Возвращает все сохраненные состояния плееров для всех гильдий.
        
        Returns:
            Список кортежей (guild_id, channel_id, message_id).
        """
        settings = await Setting.filter(key__startswith="discord_player_msg_").all()
        results = []
        for s in settings:
            try:
                parts = s.key.split("_")
                guild_id = int(parts[-1])
                data = json.loads(s.value)
                results.append((guild_id, data["channel_id"], data["message_id"]))
            except (ValueError, json.JSONDecodeError, KeyError, IndexError):
                continue
        return results
