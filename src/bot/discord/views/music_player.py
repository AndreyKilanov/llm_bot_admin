import asyncio
import logging
from typing import TYPE_CHECKING, Union

import discord
from discord.ext import commands

from src.services import music_service, SettingsService
from src.bot.discord.player import LoopMode
from .base import BaseMusicView
from .constants import (
    DEFAULT_EMBED_COLOR,
    SUCCESS_COLOR,
    PROGRESS_BAR_LENGTH,
    EMOJI_PREVIOUS,
    EMOJI_PLAY,
    EMOJI_PAUSE,
    EMOJI_NEXT,
    EMOJI_STOP,
    EMOJI_REWIND,
    EMOJI_FORWARD,
    EMOJI_QUEUE,
    EMOJI_LOOP_NONE,
    EMOJI_LOOP_TRACK,
    EMOJI_LOOP_PLAYLIST,
    EMOJI_ERROR,
    MSG_ERR_FIRST_TRACK,
    MSG_ERR_LAST_TRACK,
    MSG_ERR_PLAY_FAIL,
    MSG_ERR_RESUME_FAIL,
    MSG_ERR_PAUSE_FAIL,
    MSG_STOPPED,
    MSG_ERR_NO_ACTIVE_TRACK,
    MSG_ERR_SEEK_FAIL,
    MSG_ERR_QUEUE_EMPTY,
    MSG_QUEUE_TITLE,
    MSG_QUEUE_TOTAL,
    MSG_TRACK_INFO,
    MSG_QUEUE_EXTENDED,
    MSG_LOOP_CHANGED,
    MSG_LOOP_OFF,
    MSG_LOOP_TRACK,
    MSG_LOOP_PLAYLIST,
    MSG_LOOP_UNKNOWN,
    MSG_PLAYER_TITLE,
    MSG_PLAYER_EMPTY,
    MSG_NOW_PLAYING,
    MSG_DURATION,
    MSG_STATUS,
    MSG_PROGRESS,
    MSG_LOOP_MODE,
    MSG_STATUS_PAUSED,
    MSG_STATUS_PLAYING,
    MSG_STATUS_FINISHED,
    MSG_PLAYER_FOOTER,
    MSG_UNKNOWN,
)

if TYPE_CHECKING:
    from src.bot.discord.player import MusicPlayer

logger = logging.getLogger("discord.views.music_player")


class MusicPlayerView(BaseMusicView):
    """View для управления музыкальным плеером (кнопки паузы, пропуска и т.д.)."""

    def __init__(self, player: "MusicPlayer", ctx: commands.Context):
        """Инициализация View плеера.

        Args:
            player: Экземпляр MusicPlayer.
            ctx: Контекст команды.
        """
        super().__init__(timeout=None)
        self.player = player
        self.ctx = ctx
        self.message: discord.Message | None = None
        self._update_task: asyncio.Task | None = None

    async def start_auto_update(self):
        """Запуск цикла автоматического обновления сообщения плеера."""
        if self._update_task and not self._update_task.done():
            return

        async def update_loop():
            try:
                while True:
                    await asyncio.sleep(1.0)
                    if self.player.is_playing:
                        await self.update_player_message()
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Ошибка в цикле обновления плеера: {e}")

        self._update_task = asyncio.create_task(update_loop())

    @discord.ui.button(emoji=EMOJI_PREVIOUS, style=discord.ButtonStyle.secondary, custom_id="previous")
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Кнопка воспроизведения предыдущего трека."""
        await interaction.response.defer()
        if await self.player.play_previous():
            await self.update_player_message()
        else:
            await interaction.followup.send(MSG_ERR_FIRST_TRACK, ephemeral=True)

    @discord.ui.button(emoji=EMOJI_PAUSE, style=discord.ButtonStyle.primary, custom_id="pause_resume")
    async def pause_resume_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Кнопка переключения состояния пауза/воспроизведение."""
        await interaction.response.defer()

        # Случай, если плеер остановлен, но в очереди есть треки
        if not self.player.is_playing and not self.player.is_paused and self.player.queue:
            if await self.player.play_from_start():
                await self.update_player_message()
            else:
                await interaction.followup.send(MSG_ERR_PLAY_FAIL, ephemeral=True)
            return

        success = False
        if self.player.is_paused:
            success = self.player.resume()
            error_msg = MSG_ERR_RESUME_FAIL
        else:
            success = self.player.pause()
            error_msg = MSG_ERR_PAUSE_FAIL

        if success:
            await self.update_player_message()
        else:
            await interaction.followup.send(f"{EMOJI_ERROR} {error_msg}", ephemeral=True)

    @discord.ui.button(emoji=EMOJI_NEXT, style=discord.ButtonStyle.secondary, custom_id="next")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Кнопка воспроизведения следующего трека."""
        await interaction.response.defer()
        if await self.player.play_next():
            await self.update_player_message()
        else:
            await interaction.followup.send(MSG_ERR_LAST_TRACK, ephemeral=True)

    @discord.ui.button(emoji=EMOJI_STOP, style=discord.ButtonStyle.danger, custom_id="stop")
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Кнопка полной остановки и отключения бота."""
        await interaction.response.defer()
        await self.player.stop()
        await self.player.disconnect()

        if self._update_task:
            self._update_task.cancel()

        if self.message:
            await self.message.edit(
                content=MSG_STOPPED,
                embed=None,
                view=None
            )
        self.stop()

    async def _handle_seek(self, interaction: discord.Interaction, seconds: int):
        """Общая логика для кнопок перемотки.

        Args:
            interaction: Объект взаимодействия.
            seconds: Количество секунд для перемотки (отрицательное для назад).
        """
        await interaction.response.defer()
        if not self.player.current_track:
            return await interaction.followup.send(MSG_ERR_NO_ACTIVE_TRACK, ephemeral=True)

        self._set_seek_buttons_state(disabled=True)
        try:
            await self.message.edit(view=self)
            if not await self.player.seek_relative(seconds):
                direction = "вперед" if seconds > 0 else "назад"
                await interaction.followup.send(
                    MSG_ERR_SEEK_FAIL.format(direction=direction, seconds=abs(seconds)),
                    ephemeral=True
                )
        except Exception as e:
            logger.error(f"Ошибка перемотки: {e}")
        finally:
            self._set_seek_buttons_state(disabled=False)
            await self.update_player_message()

    def _set_seek_buttons_state(self, disabled: bool):
        """Блокирует или разблокирует кнопки перемотки."""
        for item in self.children:
            if isinstance(item, discord.ui.Button) and item.custom_id in ["rewind", "forward"]:
                item.disabled = disabled

    @discord.ui.button(emoji=EMOJI_REWIND, style=discord.ButtonStyle.secondary, custom_id="rewind", row=1)
    async def rewind_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Кнопка перемотки назад."""
        seek_time = await SettingsService.get_discord_seek_time()
        await self._handle_seek(interaction, -seek_time)

    @discord.ui.button(emoji=EMOJI_FORWARD, style=discord.ButtonStyle.secondary, custom_id="forward", row=1)
    async def forward_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Кнопка перемотки вперед."""
        seek_time = await SettingsService.get_discord_seek_time()
        await self._handle_seek(interaction, seek_time)

    @discord.ui.button(emoji=EMOJI_QUEUE, style=discord.ButtonStyle.secondary, custom_id="queue", row=1)
    async def queue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Кнопка отображения текущей очереди треков с поддержкой пагинации."""
        from .queue_pagination import QueuePaginationView
        
        if not self.player.queue:
            return await interaction.response.send_message(MSG_ERR_QUEUE_EMPTY, ephemeral=True)

        view = QueuePaginationView(self.player, self.ctx, items_per_page=10)
        embed = view.create_embed()
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_response()

    @discord.ui.button(emoji=EMOJI_LOOP_NONE, style=discord.ButtonStyle.secondary, custom_id="loop_mode", row=1)
    async def loop_mode_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Кнопка циклического переключения режима зацикливания."""
        await interaction.response.defer()
        mode = self.player.cycle_loop_mode()

        mode_names = {
            LoopMode.NONE: MSG_LOOP_OFF,
            LoopMode.TRACK: MSG_LOOP_TRACK,
            LoopMode.PLAYLIST: MSG_LOOP_PLAYLIST
        }

        await self.update_player_message()
        await interaction.followup.send(
            MSG_LOOP_CHANGED.format(mode=mode_names.get(mode, MSG_LOOP_UNKNOWN)),
            ephemeral=True
        )

    async def update_player_message(self):
        """Обновляет сообщение плеера с актуальными данными и состоянием кнопок."""
        if not self.message:
            return

        self._update_buttons_ui()

        try:
            await self.message.edit(embed=self.create_player_embed(), view=self)
        except Exception as e:
            logger.debug(f"Не удалось обновить сообщение плеера (возможно, оно удалено): {e}")

    def _update_buttons_ui(self):
        """Обновляет эмодзи и стили кнопок в зависимости от состояния плеера."""
        for item in self.children:
            if not isinstance(item, discord.ui.Button):
                continue

            if item.custom_id == "pause_resume":
                item.emoji = EMOJI_PLAY if (self.player.is_paused or (not self.player.is_playing and self.player.queue)) else EMOJI_PAUSE

            elif item.custom_id == "loop_mode":
                self._update_loop_button(item)

    def _update_loop_button(self, button: discord.ui.Button):
        """Обновляет состояние кнопки режима зацикливания."""
        if self.player.loop_mode == LoopMode.NONE:
            button.emoji = self._get_custom_emoji("norepeat", EMOJI_LOOP_NONE)
            button.style = discord.ButtonStyle.secondary
        elif self.player.loop_mode == LoopMode.TRACK:
            button.emoji = self._get_custom_emoji("repeat1", EMOJI_LOOP_TRACK)
            button.style = discord.ButtonStyle.success
        elif self.player.loop_mode == LoopMode.PLAYLIST:
            emoji = self._get_custom_emoji("repeat-1", None)
            if not emoji:
                emoji = self._get_custom_emoji("repeat_1", EMOJI_LOOP_PLAYLIST)
            button.emoji = emoji
            button.style = discord.ButtonStyle.success

    def _get_custom_emoji(self, name: str, default: str | None) -> Union[discord.Emoji, discord.PartialEmoji, str, None]:
        """Пытается получить кастомный эмодзи с сервера или возвращает стандартный.

        Args:
            name: Имя кастомного эмодзи.
            default: Эмодзи по умолчанию (строка или None).

        Returns:
            Объект эмодзи или строка.
        """
        if self.message and self.message.guild:
            emoji = discord.utils.get(self.message.guild.emojis, name=name)
            if emoji:
                return emoji
        return default

    def create_player_embed(self) -> discord.Embed:
        """Создает информативный Embed с текущим состоянием плеера.

        Returns:
            Объект discord.Embed.
        """
        track = self.player.current_track
        if not track:
            return discord.Embed(
                title=MSG_PLAYER_TITLE,
                description=MSG_PLAYER_EMPTY,
                color=DEFAULT_EMBED_COLOR
            )

        queue_info = self.player.get_queue_info()
        pos, duration_sec = self.player.get_playback_position()

        embed = discord.Embed(
            title=MSG_NOW_PLAYING,
            description=f"**{track['uploader']}**\n[{track['title']}]({track['url']})",
            color=DEFAULT_EMBED_COLOR,
            url=track['url']
        )

        embed.add_field(name=MSG_DURATION, value=music_service.format_duration(track.get("duration") or 0), inline=True)
        if track.get('thumbnail'):
            embed.set_thumbnail(url=track['thumbnail'])

        self._add_status_field(embed)
        self._add_progress_field(embed, pos, duration_sec)
        self._add_loop_field(embed)

        embed.set_footer(text=MSG_PLAYER_FOOTER.format(current=queue_info['current_index'] + 1, total=queue_info['total']))
        return embed

    def _add_status_field(self, embed: discord.Embed):
        """Добавляет поле статуса в Embed."""
        if self.player.is_paused:
            status = MSG_STATUS_PAUSED
        elif self.player.is_playing:
            status = MSG_STATUS_PLAYING
        else:
            status = MSG_STATUS_FINISHED
        embed.add_field(name=MSG_STATUS, value=status, inline=True)

    def _add_progress_field(self, embed: discord.Embed, pos: int, total: int):
        """Добавляет поле прогресс-бара в Embed."""
        if total <= 0:
            return

        progress = pos / total if (self.player.is_playing or self.player.is_paused) else 1.0
        filled = max(0, min(int(PROGRESS_BAR_LENGTH * progress), PROGRESS_BAR_LENGTH))

        # Отрисовка полосы прогресса
        if filled == 0:
            bar = "○" + "─" * (PROGRESS_BAR_LENGTH - 1)
        elif filled >= PROGRESS_BAR_LENGTH:
            bar = "─" * (PROGRESS_BAR_LENGTH - 1) + "●"
        else:
            bar = "─" * (filled - 1) + "●" + "─" * (PROGRESS_BAR_LENGTH - filled)

        pos_str = music_service.format_duration(pos)
        total_str = music_service.format_duration(total)
        embed.add_field(name=MSG_PROGRESS, value=f"`{pos_str}` {bar} `{total_str}`", inline=False)

    def _add_loop_field(self, embed: discord.Embed):
        """Добавляет информацию о режиме зацикливания в Embed."""
        if self.player.loop_mode == LoopMode.NONE:
            return

        if self.player.loop_mode == LoopMode.TRACK:
            emoji = self._get_custom_emoji("repeat1", EMOJI_LOOP_TRACK)
            label = MSG_LOOP_TRACK.capitalize()
        else:
            emoji = self._get_custom_emoji("repeat-1", None) or self._get_custom_emoji("repeat_1", EMOJI_LOOP_PLAYLIST)
            label = MSG_LOOP_PLAYLIST.capitalize()

        embed.add_field(name=f"{emoji} {MSG_LOOP_MODE}", value=label, inline=True)
