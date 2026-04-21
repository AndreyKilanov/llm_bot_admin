"""Модуль команд инициализации воспроизведения плеера.

Содержит команды `play`, `link`, `playlist` и слэш-поиск.
"""

import asyncio
import logging
import time
from typing import Union

import discord
from discord import app_commands
from discord.ext import commands

from src.bot.discord.views import TrackSelectionView
from src.bot.discord.views.emoji_manager import emoji_manager
from src.bot.discord.views.constants import commands_config, ui_config
from src.services import music_service, SettingsService
from .base import BaseMusicCog

logger = logging.getLogger("discord.music_cog.playback")


class PlaybackCommands(BaseMusicCog):
    """Ког для запуска воспроизведения и поиска треков."""

    @commands.hybrid_command(
        name=commands_config.play.name, 
        description=commands_config.play.description
    )
    async def play_music_cmd(self, ctx: commands.Context, *, query: str) -> None:
        """Команда для поиска и воспроизведения музыки.

        Args:
            ctx: Контекст команды.
            query: Поисковый запрос.
        """
        await ctx.defer()
        await self._handle_play_logic(ctx, query)

    async def _handle_play_logic(self, ctx: Union[commands.Context, discord.Interaction], query: str) -> None:
        """Внутренняя логика поиска и запуска воспроизведения.

        Args:
            ctx: Контекст или взаимодействие.
            query: Запрос для поиска.
        """
        v_channel = await self.verify_ready(ctx)
        if not v_channel:
            return

        e = emoji_manager.get_all()
        send_method = ctx.send if isinstance(ctx, commands.Context) else ctx.followup.send
        status_msg = await send_method(f"{e.search} Поиск: **{query}**...")
        tracks = await music_service.search_tracks(query, max_results=ui_config.max_search_results)

        if not tracks:
            await status_msg.edit(content=ui_config.msg_search_fail)
            await self._delete_with_delay(status_msg, ui_config.notification_timeout)
            return

        if len(tracks) == 1:
            track = tracks[0]
            await status_msg.edit(content=f"{e.success} Трек найден и добавлен: **{track.title}**")
            await self.start_playback_sequence(ctx, tracks, v_channel)
            return

        guild_id = ctx.guild.id if isinstance(ctx, commands.Context) else ctx.guild_id
        if not guild_id:
            return
            
        player = self.get_player(guild_id)
        view = TrackSelectionView(tracks, player, ctx)
        embed = view.create_embed()
        await status_msg.edit(content=None, embed=embed, view=view)
        view.message = status_msg

    @commands.hybrid_command(
        name=commands_config.link.name, 
        description=commands_config.link.description
    )
    async def play_link_cmd(self, ctx: commands.Context, *, url: str) -> None:
        """Воспроизведение по прямой ссылке.

        Args:
            ctx: Контекст команды.
            url: Прямая ссылка на трек.
        """
        await ctx.defer()
        v_channel = await self.verify_ready(ctx)
        if not v_channel:
            return
            
        if not music_service.is_valid_url(url):
            await ctx.send(ui_config.msg_invalid_url, delete_after=ui_config.notification_timeout)
            return

        e = emoji_manager.get_all()
        status_msg = await ctx.send(f"{e.search} Загрузка: <{url}>...")
        info = await music_service.get_track_info(url)
        
        if not info:
            await status_msg.edit(content=ui_config.msg_load_fail)
            return

        await status_msg.edit(content=f"{e.success} Трек добавлен: **{info.title}**")
        await self.start_playback_sequence(ctx, [info], v_channel)

    @commands.hybrid_command(
        name=commands_config.playlist.name, 
        description=commands_config.playlist.description
    )
    async def play_playlist_cmd(self, ctx: commands.Context, *, url: str) -> None:
        """Загрузка и воспроизведение плейлиста.

        Args:
            ctx: Контекст команды.
            url: Ссылка на плейлист.
        """
        await ctx.defer()
        v_channel = await self.verify_ready(ctx)
        if not v_channel:
            return
            
        if not music_service.is_valid_url(url):
            await ctx.send(ui_config.msg_invalid_url, delete_after=ui_config.notification_timeout)
            return

        e = emoji_manager.get_all()
        status_msg = await ctx.send(f"{e.search} Загрузка плейлиста: <{url}>...")
        tracks = await music_service.get_playlist_info(url)
        
        if not tracks:
            await status_msg.edit(content=f"{e.error} Не удалось загрузить плейлист.")
            return

        await status_msg.edit(content=f"{e.success} Найдено {len(tracks)} треков. Добавляю в очередь...")
        await self.start_playback_sequence(ctx, tracks, v_channel)

    @app_commands.command(
        name=commands_config.search.name, 
        description=commands_config.search.description
    )
    @app_commands.describe(query="Введите название трека или выберите из списка")
    async def search_slash(self, interaction: discord.Interaction, query: str) -> None:
        """Слэш-команда живого поиска.

        Args:
            interaction: Объект взаимодействия Discord.
            query: Поисковый запрос.
        """
        try:
            await interaction.response.defer()
        except discord.NotFound:
            return
            
        if not await SettingsService.is_discord_bot_enabled():
            await interaction.followup.send(ui_config.msg_bot_disabled, ephemeral=True)
            return

        if not await SettingsService.is_discord_music_enabled():
            await interaction.followup.send(ui_config.msg_music_disabled, ephemeral=True)
            return

        if not interaction.user.voice:
            try:
                await interaction.followup.send(ui_config.msg_voice_required, ephemeral=True)
            except discord.HTTPException:
                pass
            return

        v_channel = interaction.user.voice.channel
        e = emoji_manager.get_all()

        try:
            if music_service.is_valid_url(query):
                try:
                    info = await asyncio.wait_for(music_service.get_track_info(query), timeout=30.0)
                except asyncio.TimeoutError:
                    await interaction.followup.send("⚠️ Время ожидания поиска истекло.", ephemeral=True)
                    return
                
                if not info:
                    await interaction.followup.send(ui_config.msg_load_fail, ephemeral=True)
                    return

                await interaction.followup.send(f"{e.success} Добавлено: **{info.title}**", ephemeral=True)
                await self.start_playback_sequence(interaction, [info], v_channel)
                return

            try:
                tracks = await asyncio.wait_for(music_service.search_tracks(query, max_results=ui_config.max_search_results), timeout=30.0)
            except asyncio.TimeoutError:
                await interaction.followup.send("⚠️ Время ожидания поиска истекло.", ephemeral=True)
                return

            if not tracks:
                await interaction.followup.send(ui_config.msg_search_fail, ephemeral=True)
                return

            if len(tracks) == 1:
                e = emoji_manager.get_all()
                await interaction.followup.send(f"{e.success} Добавлено: **{tracks[0].title}**", ephemeral=True)
                await self.start_playback_sequence(interaction, tracks, v_channel)
            else:
                if not interaction.guild_id:
                    return
                player = self.get_player(interaction.guild_id)
                view = TrackSelectionView(tracks, player, interaction)
                embed = view.create_embed()
                msg = await interaction.followup.send(embed=embed, view=view)
                view.message = msg

        except (discord.NotFound, discord.HTTPException) as exc:
            if isinstance(exc, discord.NotFound) and exc.code in (10062, 10015):
                logger.debug("search_slash: токен взаимодействия истёк или не найден: %s", exc)
            else:
                logger.error("search_slash: ошибка при отправке followup: %s", exc)

    @search_slash.autocomplete("query")
    async def search_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Живой поиск треков для автодополнения.

        Args:
            interaction: Объект взаимодействия.
            current: Текущая строка ввода пользователя.

        Returns:
            list[app_commands.Choice[str]]: Список вариантов для выбора.
        """
        try:
            if not current.strip():
                return []

            start_time = time.monotonic()

            if not await SettingsService.is_discord_bot_enabled():
                return []
            if not await SettingsService.is_discord_music_enabled():
                return []

            tracks = await music_service.search_tracks_fast(
                current, 
                max_results=ui_config.autocomplete_max_results
            )
            elapsed = time.monotonic() - start_time
            logger.info(f"Сверхбыстрый YouTube поиск: '{current}' -> {len(tracks)} треков за {elapsed:.3f}с")

            choices = []
            search_label = ui_config.autocomplete_search_prefix.format(query=current)
            choices.append(app_commands.Choice(
                name=search_label[:ui_config.autocomplete_choice_limit], 
                value=current[:ui_config.autocomplete_choice_limit]
            ))

            for t in tracks[:ui_config.autocomplete_loop_limit]:
                title = t.title[:ui_config.autocomplete_title_limit]
                uploader = t.uploader[:ui_config.autocomplete_uploader_limit]
                name = f"{title}{ui_config.autocomplete_separator}{uploader}"
                choices.append(app_commands.Choice(
                    name=name[:ui_config.autocomplete_choice_limit], 
                    value=str(t.url)
                ))

            return choices
        except Exception as e:
            logger.error(f"Аварийная ошибка в автодополнении поиска: {e}", exc_info=True)
            fallback_label = current[:ui_config.autocomplete_choice_limit]
            return [app_commands.Choice(name=fallback_label, value=fallback_label)] if current.strip() else []
