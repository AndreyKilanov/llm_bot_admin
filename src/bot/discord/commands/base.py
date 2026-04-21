"""Базовый модуль для музыкальных команд Discord бота.

Содержит общий класс с вспомогательными методами для работы с плеером.
"""

import asyncio
import logging
from typing import Optional, Union

import discord
from discord.ext import commands

from src.bot.discord.player import MusicPlayer, PlayerFactory
from src.bot.discord.views import MusicPlayerView
from src.services import SettingsService
from src.schemas import TrackInfo
from src.bot.discord.views.constants import ui_config
from src.services.player_state_service import PlayerStateService

logger = logging.getLogger("discord.music_cog.base")


class BaseMusicCog(commands.Cog):
    """Базовый класс для всех когов музыкального плеера.
    
    Инкапсулирует общую логику: проверки, инициализация плеера, отправка UI.
    """

    def __init__(self, bot: commands.Bot) -> None:
        """Инициализирует базовый ког.

        Args:
            bot: Экземпляр бота discord.py.
        """
        self.bot = bot

    async def _delete_with_delay(self, message: Union[discord.Message, discord.WebhookMessage], delay: float) -> None:
        """Безопасно удаляет сообщение через указанную задержку.

        Args:
            message: Сообщение для удаления.
            delay: Задержка в секундах перед удалением.
        """
        try:
            await message.delete(delay=delay)
        except (TypeError, discord.HTTPException, discord.Forbidden):
            async def delayed_delete() -> None:
                await asyncio.sleep(delay)
                try:
                    await message.delete()
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    pass
            
            asyncio.create_task(delayed_delete())

    def get_player(self, guild_id: int) -> MusicPlayer:
        """Возвращает экземпляр музыкального плеера для конкретного сервера.

        Args:
            guild_id: ID сервера (guild).

        Returns:
            MusicPlayer: Экземпляр плеера.
        """
        return PlayerFactory.get_player(guild_id, self.bot)

    async def verify_ready(self, ctx: Union[commands.Context, discord.Interaction]) -> Optional[discord.VoiceChannel]:
        """Проверяет готовность бота и пользователя к воспроизведению.

        Args:
            ctx: Контекст команды или взаимодействие.

        Returns:
            Optional[discord.VoiceChannel]: Голосовой канал автора, если все проверки пройдены.
        """
        if not await SettingsService.is_discord_bot_enabled():
            if isinstance(ctx, commands.Context):
                await ctx.send(ui_config.msg_bot_disabled, delete_after=ui_config.notification_timeout)
            else:
                await ctx.response.send_message(ui_config.msg_bot_disabled, ephemeral=True)
            return None

        if not await SettingsService.is_discord_music_enabled():
            if isinstance(ctx, commands.Context):
                await ctx.send(ui_config.msg_music_disabled, delete_after=ui_config.notification_timeout)
            else:
                await ctx.response.send_message(ui_config.msg_music_disabled, ephemeral=True)
            return None

        user = ctx.author if isinstance(ctx, commands.Context) else ctx.user
        if not user.voice or not user.voice.channel:
            if isinstance(ctx, commands.Context):
                await ctx.send(ui_config.msg_voice_required, delete_after=ui_config.notification_timeout)
            else:
                await ctx.response.send_message(ui_config.msg_voice_required, ephemeral=True)
            return None

        return user.voice.channel

    async def start_playback_sequence(
        self, 
        ctx: Union[commands.Context, discord.Interaction], 
        tracks: list[TrackInfo], 
        channel: discord.VoiceChannel
    ) -> None:
        """Инициализирует последовательность воспроизведения треков.

        Args:
            ctx: Контекст команды или взаимодействие.
            tracks: Список информации о треках для добавления.
            channel: Голосовой канал для подключения.
        """
        guild_id = ctx.guild.id if isinstance(ctx, commands.Context) else ctx.guild_id
        if not guild_id:
            return

        text_channel = ctx.channel
        user = ctx.author if isinstance(ctx, commands.Context) else ctx.user
        author_name = user.display_name

        player = self.get_player(guild_id)
        player.set_text_channel(text_channel)

        if not await player.connect(channel):
            if isinstance(ctx, commands.Context):
                await ctx.send(ui_config.msg_conn_fail, delete_after=ui_config.notification_timeout)
            else:
                await ctx.response.send_message(ui_config.msg_conn_fail, ephemeral=True)
            return

        for track in tracks:
            if not track.added_by:
                track.added_by = author_name
            if not track.source:
                track.source = self._detect_source(str(track.url))

        player.add_to_queue(tracks)

        if not player.is_playing:
            await player.play_from_start()

        await self.send_player_ui(ctx, player)

    def _detect_source(self, url: str) -> str:
        """Определить источник трека по URL.

        Args:
            url: Ссылка на трек.

        Returns:
            str: Код источника ('youtube', 'vk' или 'unknown').
        """
        if "youtube.com" in url or "youtu.be" in url:
            return "youtube"
        if "vk.com" in url or "vk.ru" in url:
            return "vk"
        return "unknown"

    async def send_player_ui(self, ctx: Union[commands.Context, discord.Interaction], player: MusicPlayer) -> None:
        """Отправляет сообщение с интерфейсом управления плеером.

        Args:
            ctx: Контекст или взаимодействие.
            player: Экземпляр плеера для текущей гильдии.
        """
        if not player.current_track:
            return

        guild_id = player.guild_id
        
        if player.player_message:
            await player.clear_player_ui()
        else:
            state = await PlayerStateService.get_player_msg(guild_id)
            if state:
                ch_id, msg_id = state
                try:
                    target_channel = self.bot.get_channel(ch_id) or await self.bot.fetch_channel(ch_id)
                    if isinstance(target_channel, discord.TextChannel):
                        old_msg = await target_channel.fetch_message(msg_id)
                        await old_msg.delete()
                        logger.info("Удалено устаревшее сообщение плеера на сервере %d", guild_id)
                except Exception:
                    pass
                await PlayerStateService.clear_player_msg(guild_id)

        view = MusicPlayerView(player, ctx)
        embed = view.create_player_embed()
        
        if isinstance(ctx, commands.Context):
            message = await ctx.channel.send(embed=embed, view=view)
        else:
            if ctx.response.is_done():
                message = await ctx.followup.send(embed=embed, view=view)
            else:
                await ctx.response.send_message(embed=embed, view=view)
                message = await ctx.original_response()
        
        player.player_view = view
        player.player_message = message
        view.message = message
        
        await PlayerStateService.save_player_msg(guild_id, message.channel.id, message.id)
        
        await view.start_auto_update()
