"""Менеджер Application Emojis для музыкального плеера Discord.

Загружает кастомные иконки один раз на уровне приложения через Discord API.
Emoji работают на всех серверах где есть бот — без загрузки на каждый сервер.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Final

import discord
from src.schemas import BotEmojis

if TYPE_CHECKING:
    pass

logger = logging.getLogger("discord.emoji_manager")


class EmojiManager:
    """Менеджер Application Emojis для кнопок плеера.

    Загружает PNG-иконки как Application Emojis при on_ready.
    При повторном запуске переиспользует уже загруженные emoji.
    Если emoji недоступен — возвращает Unicode fallback из BotEmojis.
    """

    ICONS_DIR: Final[Path] = Path("src/bot/discord/assets/icons")

    def __init__(self) -> None:
        """Инициализация менеджера без подключения к Discord."""
        self._emojis: dict[str, discord.Emoji] = {}
        self._cached_schema: BotEmojis | None = None
        self._default_emojis = BotEmojis()
        self._initialized: bool = False

    async def initialize(self, bot: discord.Client) -> None:
        """Загрузить и обновить Application Emojis.

        Принудительно удаляет старые иконки и загружает актуальные из
        ``src/bot/discord/assets/icons``, чтобы они всегда соответствовали
        локальным файлам и имели единый стиль.
        """
        if self._initialized:
            return

        logger.info("Синхронизация Application Emojis...")

        try:
            existing_emojis = await bot.fetch_application_emojis()
        except discord.HTTPException as exc:
            logger.error("Не удалось получить список иконок: %s", exc)
            self._initialized = True
            return

        for emoji in existing_emojis:
            try:
                await emoji.delete()
                logger.debug("Старая иконка удалена: :%s:", emoji.name)
            except discord.HTTPException:
                pass

        self._emojis.clear()
        loaded = 0
        failed = 0

        for name in BotEmojis.model_fields.keys():
            icon_path = self.ICONS_DIR / f"{name}.png"
            if not icon_path.exists():
                logger.warning(
                    "Файл иконки не найден: %s. Будет использован Unicode fallback из BotEmojis",
                    icon_path,
                )
                continue

            try:
                emoji = await bot.create_application_emoji(
                    name=name,
                    image=icon_path.read_bytes(),
                )
                self._emojis[name] = emoji
                loaded += 1
                logger.debug("Иконка обновлена: :%s:", name)
            except discord.HTTPException as exc:
                logger.warning("Ошибка загрузки иконки '%s': %s", name, exc)
                failed += 1

        self._initialized = True
        self._cached_schema = None
        logger.info(
            "Синхронизация иконок завершена: %d обновлено, %d не удалось.",
            loaded,
            failed,
        )

    def get(self, name: str) -> discord.Emoji | str:
        """Получить emoji по имени.

        Возвращает кастомный Application Emoji если загружен,
        иначе Unicode fallback из EMOJI_FALLBACK.

        Args:
            name: Имя emoji (ключ в EMOJI_FALLBACK).

        Returns:
            discord.Emoji или Unicode строка.
        """
        if name in self._emojis:
            return self._emojis[name]
        
        return getattr(self._default_emojis, name, "❓")
    
    def get_all(self) -> BotEmojis:
        """Возвращает Pydantic-схему со всеми актуальными эмодзи.
        
        Объект кэшируется после первого вызова до следующей инициализации/сброса.
        
        Returns:
            BotEmojis: Схема со всеми иконками.
        """
        if self._cached_schema:
            return self._cached_schema
            
        data = {name: self.get(name) for name in BotEmojis.model_fields.keys()}
        self._cached_schema = BotEmojis(**data)
        return self._cached_schema

    def reset(self) -> None:
        """Сбросить состояние (для повторной инициализации при рестарте)."""
        self._emojis.clear()
        self._cached_schema = None
        self._initialized = False


emoji_manager = EmojiManager()
