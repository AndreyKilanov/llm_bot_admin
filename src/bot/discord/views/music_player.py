import asyncio
import logging
from typing import TYPE_CHECKING, Union

import discord
from discord.ext import commands

from src.services import music_service, lyrics_service
from src.bot.discord.player import LoopMode
from .base import BaseMusicView
from .emoji_manager import emoji_manager
from .queue_pagination import QueuePaginationView
from .constants import ui_config

if TYPE_CHECKING:
    from src.bot.discord.player import MusicPlayer

logger = logging.getLogger("discord.views.music_player")


class MusicPlayerView(BaseMusicView):
    """View для управления музыкальным плеером (3 ряда кнопок)."""

    def __init__(self, player: "MusicPlayer", ctx: Union[commands.Context, discord.Interaction]):
        super().__init__(timeout=None)
        self.player = player
        self.ctx = ctx
        self.message: discord.Message | discord.InteractionMessage | None = None
        self._update_task: asyncio.Task | None = None
        self._update_buttons_ui()

    async def start_auto_update(self):
        """Запуск цикла автоматического обновления сообщения плеера."""
        if self._update_task and not self._update_task.done():
            return

        async def update_loop():
            try:
                while True:
                    await asyncio.sleep(1.0)
                    if self.player.is_playing and not self.player.is_paused:
                        await self.update_player_message()
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Ошибка в цикле обновления плеера: {e}")

        self._update_task = asyncio.create_task(update_loop())

    def stop_auto_update(self):
        """Остановка цикла автоматического обновления."""
        if self._update_task and not self._update_task.done():
            self._update_task.cancel()
            self._update_task = None
            logger.debug(f"Цикл обновления плеера остановлен на сервере {self.player.guild_id}")

    @discord.ui.button(custom_id="previous", row=0)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if not await self.player.play_previous():
            await interaction.followup.send(ui_config.msg_err_first_track, ephemeral=True)
        await self.update_player_message()

    @discord.ui.button(custom_id="rewind", row=0)
    async def rewind_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_seek(interaction, -10)

    @discord.ui.button(custom_id="pause_resume", row=0)
    async def pause_resume_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        success = False
        if not self.player.is_playing and not self.player.is_paused and self.player.queue:
            success = await self.player.play_from_start()
        elif self.player.is_paused:
            success = self.player.resume()
        else:
            success = self.player.pause()

        if success:
            await self.update_player_message()
        else:
            e = emoji_manager.get_all()
            await interaction.followup.send(f"{e.error} {ui_config.msg_error}", ephemeral=True)

    @discord.ui.button(custom_id="forward", row=0)
    async def forward_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_seek(interaction, 10)

    @discord.ui.button(custom_id="next", row=0)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if not await self.player.play_next():
            await interaction.followup.send(ui_config.msg_err_last_track, ephemeral=True)
        await self.update_player_message()

    @discord.ui.button(custom_id="shuffle", row=1)
    async def shuffle_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.player.shuffle_queue()
        await interaction.response.defer()
        await self.update_player_message()

    @discord.ui.button(custom_id="loop_mode", row=1)
    async def loop_mode_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.player.cycle_loop_mode()
        await interaction.response.defer()
        await self.update_player_message()

    @discord.ui.button(custom_id="queue", row=1)
    async def queue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.player.queue:
            return await interaction.response.send_message(ui_config.msg_err_queue_empty, ephemeral=True)
        view = QueuePaginationView(self.player, self.ctx, items_per_page=10)
        await interaction.response.send_message(embed=view.create_embed(), view=view, ephemeral=True)

    @discord.ui.button(custom_id="lyrics", row=1)
    async def lyrics_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        track = self.player.current_track
        if not track:
            return await interaction.followup.send(ui_config.msg_err_no_active_track, ephemeral=True)

        content = await lyrics_service.get_lyrics(track.title, track.uploader or '')
        if not content:
            return await interaction.followup.send(ui_config.msg_no_lyrics, ephemeral=True)

        embed = discord.Embed(
            title=f"Текст песни: {track.title}",
            description=content,
            color=ui_config.embed_color
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(custom_id="stop_only", row=1)
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Остановка без выхода из канала."""
        await interaction.response.defer()
        await self.player.stop_playback_only()
        msg = await interaction.followup.send(ui_config.msg_playback_stopped)
        await self._delete_with_delay(msg, ui_config.notification_timeout)
        await self.update_player_message()

    @discord.ui.button(custom_id="mute", row=2)
    async def mute_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.player.toggle_mute()
        await self.update_player_message()

    @discord.ui.button(custom_id="vol_down", row=2)
    async def vol_down_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.player.set_volume(self.player.volume - 0.2)
        await self.update_player_message()

    @discord.ui.button(custom_id="vol_up", row=2)
    async def vol_up_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.player.volume >= 1.0:
            return await interaction.response.send_message(
                ui_config.msg_volume_max,
                ephemeral=True
            )
        
        await interaction.response.defer()
        self.player.set_volume(self.player.volume + 0.2)
        await self.update_player_message()

    @discord.ui.button(custom_id="add_query", row=2)
    async def add_query_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Открывает модальное окно для быстрого поиска музыки."""
        await interaction.response.send_modal(SearchModal(self.player.bot, self.player))

    @discord.ui.button(custom_id="disconnect", row=2)
    async def disconnect_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Полная остановка и выход из канала."""
        await interaction.response.defer()
        await self.player.disconnect()
        self.stop_auto_update()
        self.stop()

    async def _handle_seek(self, interaction: discord.Interaction, seconds: int):
        await interaction.response.defer()
        if not self.player.current_track:
            return await interaction.followup.send(ui_config.msg_err_no_active_track, ephemeral=True)
        await self.player.seek_relative(seconds)
        await self.update_player_message()

    async def update_player_message(self):
        """Обновляет сообщение плеера с актуальными данными и состоянием кнопок."""
        if not self.message:
            return
        self._update_buttons_ui()
        try:
            await self.message.edit(embed=self.create_player_embed(), view=self)
        except Exception:
            pass

    def _update_buttons_ui(self):
        """Обновляет эмодзи и стили кнопок в зависимости от состояния плеера."""
        e = emoji_manager.get_all()
        for item in self.children:
            if not isinstance(item, discord.ui.Button):
                continue

            item.label = None

            if item.custom_id == "pause_resume":
                show_play = self.player.is_paused or not self.player.is_playing
                item.emoji = e.play if show_play else e.pause
                item.style = discord.ButtonStyle(ui_config.style_primary) if not show_play else discord.ButtonStyle(ui_config.style_secondary)

            elif item.custom_id == "loop_mode":
                if self.player.loop_mode == LoopMode.NONE:
                    item.emoji = e.norepeat
                    item.style = discord.ButtonStyle(ui_config.style_secondary)
                else:
                    item.emoji = e.repeat_all if self.player.loop_mode == LoopMode.PLAYLIST else e.repeat1
                    item.style = discord.ButtonStyle(ui_config.style_success)

            elif item.custom_id in ["vol_down", "vol_up"]:
                item.emoji = getattr(e, item.custom_id)
                item.style = discord.ButtonStyle(ui_config.style_secondary)
        
            elif item.custom_id == "mute":
                item.emoji = e.mute if self.player.is_muted else e.unmute
                item.style = discord.ButtonStyle(ui_config.style_danger) if self.player.is_muted else discord.ButtonStyle(ui_config.style_secondary)
            
            elif item.custom_id == "add_query":
                item.emoji = e.add_query
                item.style = discord.ButtonStyle(ui_config.style_success)

            elif item.custom_id == "disconnect":
                item.emoji = e.disconnect
                item.style = discord.ButtonStyle(ui_config.style_danger)

            else:
                item.emoji = getattr(e, item.custom_id, item.emoji)
                item.style = discord.ButtonStyle(ui_config.style_secondary)

    def create_player_embed(self) -> discord.Embed:
        """Создает информативный Embed согласно референсу."""
        track = self.player.current_track
        if not track:
            return discord.Embed(title="Плеер", description=ui_config.msg_player_empty, color=ui_config.embed_color)

        pos, duration_sec = self.player.get_playback_position()

        track_url = track.url
        uploader = track.uploader or 'Неизвестно'

        embed = discord.Embed(
            title=track.title,
            url=track_url if track_url and track_url.strip() else None,
            description=f"**Исполнитель:** `{uploader}`",
            color=ui_config.embed_color
        )
        embed.set_author(name=ui_config.msg_now_playing)

        thumbnail = track.thumbnail
        if thumbnail and thumbnail.strip():
            embed.set_thumbnail(url=thumbnail)

        progress = pos / duration_sec if duration_sec > 0 else 0
        filled = int(ui_config.progress_bar_length * progress)
        bar = "━" * filled + "⚪" + "━" * (ui_config.progress_bar_length - filled - 1)
        pos_str = music_service.format_duration(pos)
        total_str = music_service.format_duration(duration_sec)
        embed.add_field(name=ui_config.msg_progress, value=f"`{pos_str}` {bar} `{total_str}`", inline=False)
        self._add_status_fields(embed)
        total_tracks = len(self.player.queue)
        current_idx = self.player.current_index + 1
        footer_text = ui_config.msg_player_footer.format(current=current_idx, total=total_tracks)
        embed.set_footer(text=f"{footer_text}{ui_config.invisible_spacer}")
        
        return embed

    def _add_status_fields(self, embed: discord.Embed):
        """Добавляет информацию о громкости и режиме зацикливания в одну строку."""
        e = emoji_manager.get_all()
        vol = self.player.volume
        vol_percent = int(vol * 100)
        is_muted = self.player.is_muted
        vol_emoji = e.mute if is_muted else e.unmute
        
        if is_muted:
            vol_bar = "───"
            vol_text = "Заглушено"
        else:
            filled = int(15 * vol)
            vol_bar = "▇" * filled + "─" * (15 - filled)
            vol_text = f"{vol_percent}%"
        
        embed.add_field(name="\u200b", value=f"{vol_emoji} **Громкость:** `{vol_bar}` **{vol_text}**", inline=False)

        mode = self.player.loop_mode
        if mode == LoopMode.TRACK:
            emoji = e.repeat1
            label = ui_config.msg_loop_track.capitalize()
        elif mode == LoopMode.PLAYLIST:
            emoji = e.repeat_all
            label = ui_config.msg_loop_playlist.capitalize()
        else:
            emoji = e.norepeat
            label = ui_config.msg_loop_off.capitalize()

        embed.add_field(name="\u200b", value=f"{emoji} **{ui_config.msg_loop_mode}:** {label}", inline=False)


class SearchModal(discord.ui.Modal):
    """Диалоговое окно для ввода поискового запроса или ссылки."""
    
    def __init__(self, bot: commands.Bot, player: "MusicPlayer"):
        super().__init__(title=ui_config.msg_search_modal_title)
        self.bot = bot
        self.player = player
        
        self.query = discord.ui.TextInput(
            label=ui_config.msg_search_modal_label,
            placeholder=ui_config.msg_search_modal_placeholder,
            min_length=2,
            max_length=200,
            required=True
        )
        self.add_item(self.query)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        cog = self.bot.get_cog("MusicCog")
        if cog:
            await cog._handle_play_logic(interaction, self.query.value)
        else:
            await interaction.followup.send(ui_config.msg_cog_missing, ephemeral=True)
