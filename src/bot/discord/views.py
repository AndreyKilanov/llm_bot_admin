import asyncio
import logging
from typing import Optional

import discord
from discord.ext import commands

from src.services import music_service, SettingsService
from src.bot.discord.music_player import LoopMode


logger = logging.getLogger("discord.views")


class TrackSelectionView(discord.ui.View):
    """View для выбора трека из списка."""

    def __init__(self, tracks: list[dict], player, ctx: commands.Context):
        """
        Инициализация view для выбора трека.
        
        Args:
            tracks: Список найденных треков
            player: Экземпляр MusicPlayer
            ctx: Контекст команды
        """
        super().__init__(timeout=60)
        self.tracks = tracks
        self.player = player
        self.ctx = ctx
        self.message: Optional[discord.Message] = None

        for i, track in enumerate(tracks[:5], 1):
            button = discord.ui.Button(
                label=f"{i}",
                style=discord.ButtonStyle.primary,
                custom_id=f"track_{i}"
            )
            button.callback = self._create_callback(i - 1)
            self.add_item(button)

        add_all_button = discord.ui.Button(
            label="Добавить все",
            style=discord.ButtonStyle.success,
            custom_id="add_all"
        )
        add_all_button.callback = self._add_all_callback
        self.add_item(add_all_button)

    def _create_callback(self, index: int):
        """
        Создание callback для кнопки выбора трека.
        
        Args:
            index: Индекс выбранного трека
            
        Returns:
            Async callback функция
        """

        async def callback(interaction: discord.Interaction):
            if not self.ctx.author.voice:
                await interaction.response.send_message(
                    "❌ Вы больше не в голосовом канале!",
                    ephemeral=True
                )
                return

            await interaction.response.defer()
            voice_channel = self.ctx.author.voice.channel
            if not await self.player.connect(voice_channel):
                await interaction.followup.send(
                    "❌ Не удалось подключиться к голосовому каналу.",
                    ephemeral=True
                )
                return

            track = self.tracks[index]
            self.player.add_to_queue([track])

            if not self.player.is_playing:
                await self.player.play_from_start()

            await interaction.edit_original_response(
                content="✅ Трек добавлен в очередь!",
                embed=None,
                view=None
            )
            
            if self.player.current_track:
                player_view = MusicPlayerView(self.player, self.ctx)
                embed = player_view._create_player_embed()
                message = await self.ctx.send(embed=embed, view=player_view)
                
                self.player.player_view = player_view
                self.player.player_message = message
                player_view.message = message
                
                await player_view.start_auto_update()
            
            self.stop()

        return callback

    async def _add_all_callback(self, interaction: discord.Interaction):
        """Callback для кнопки "Добавить все"."""
        if not self.ctx.author.voice:
            await interaction.response.send_message(
                "❌ Вы больше не в голосовом канале!",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        voice_channel = self.ctx.author.voice.channel
        if not await self.player.connect(voice_channel):
            await interaction.followup.send(
                "❌ Не удалось подключиться к голосовому каналу.",
                ephemeral=True
            )
            return

        self.player.add_to_queue(self.tracks)

        if not self.player.is_playing:
            await self.player.play_from_start()

        await interaction.edit_original_response(
            content=f"✅ Добавлено {len(self.tracks)} треков в очередь!",
            embed=None,
            view=None
        )
        
        if self.player.current_track:
            player_view = MusicPlayerView(self.player, self.ctx)
            embed = player_view._create_player_embed()
            message = await self.ctx.send(embed=embed, view=player_view)
            
            self.player.player_view = player_view
            self.player.player_message = message
            player_view.message = message
            
            await player_view.start_auto_update()
        
        self.stop()

    async def on_timeout(self):
        """Обработка таймаута."""
        if self.message:
            try:
                await self.message.edit(
                    content="⏱️ Время выбора истекло.",
                    embed=None,
                    view=None
                )
            except:
                pass


class MusicPlayerView(discord.ui.View):
    """View для постоянного проигрывателя с кнопками управления."""

    def __init__(self, player, ctx: commands.Context):
        """
        Инициализация view для музыкального плеера.
        
        Args:
            player: Экземпляр MusicPlayer
            ctx: Контекст команды
        """
        super().__init__(timeout=None)
        self.player = player
        self.ctx = ctx
        self.message: Optional[discord.Message] = None
        self._update_task: Optional[asyncio.Task] = None
        
    async def start_auto_update(self):
        """Запуск автоматического обновления прогресс-бара."""
        if self._update_task:
            return
            
        async def update_loop():
            try:
                while True:
                    await asyncio.sleep(1.0)
                    if self.player.is_playing:
                        await self._update_player_message()
            except asyncio.CancelledError:
                pass
        
        self._update_task = asyncio.create_task(update_loop())

    @discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.secondary, custom_id="previous")
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Кнопка предыдущего трека."""
        await interaction.response.defer()

        if await self.player.play_previous():
            await self._update_player_message()
        else:
            await interaction.followup.send("❌ Это первый трек в очереди.", ephemeral=True)

    @discord.ui.button(emoji="⏸️", style=discord.ButtonStyle.primary, custom_id="pause_resume")
    async def pause_resume_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Кнопка паузы/возобновления."""
        await interaction.response.defer()

        if self.player.is_paused:
            if self.player.resume():
                button.emoji = "⏸️"
                await self._update_player_message()
            else:
                await interaction.followup.send(
                    "❌ Не удалось возобновить воспроизведение.",
                    ephemeral=True
                )
        else:
            if self.player.pause():
                button.emoji = "▶️"
                await self._update_player_message()
            else:
                await interaction.followup.send(
                    "❌ Не удалось приостановить воспроизведение.",
                    ephemeral=True
                )

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary, custom_id="next")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Кнопка следующего трека."""
        await interaction.response.defer()

        if await self.player.play_next():
            await self._update_player_message()
        else:
            await interaction.followup.send(
                "❌ Это последний трек в очереди.",
                ephemeral=True
            )

    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger, custom_id="stop")
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Кнопка остановки."""
        await interaction.response.defer()
        await self.player.stop()
        await self.player.disconnect()
        
        if self._update_task:
            self._update_task.cancel()
            self._update_task = None

        if self.message:
            await self.message.edit(
                content="⏹️ Воспроизведение остановлено.",
                embed=None,
                view=None
            )
        self.stop()

    @discord.ui.button(emoji="⏪", style=discord.ButtonStyle.secondary, custom_id="rewind", row=1)
    async def rewind_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Кнопка перемотки назад на 10 секунд."""
        await interaction.response.defer()
        
        if not self.player.current_track:
            await interaction.followup.send("❌ Нет активного трека.", ephemeral=True)
            return
        
        seek_time = await SettingsService.get_discord_seek_time()
        try:
            if await self.player.seek_relative(-seek_time):
                await self._update_player_message()
            else:
                await interaction.followup.send(f"❌ Не удалось перемотать назад на {seek_time}с.", ephemeral=True)
        except discord.errors.NotFound:
            logger.warning("Взаимодействие истекло или сообщение удалено")
        except Exception as e:
            logger.error(f"Ошибка в кнопке перемотки назад: {e}")

    @discord.ui.button(emoji="⏩", style=discord.ButtonStyle.secondary, custom_id="forward", row=1)
    async def forward_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Кнопка перемотки вперед на 10 секунд."""
        await interaction.response.defer()
        
        if not self.player.current_track:
            await interaction.followup.send("❌ Нет активного трека.", ephemeral=True)
            return
        
        seek_time = await SettingsService.get_discord_seek_time()
        try:
            if await self.player.seek_relative(seek_time):
                await self._update_player_message()
            else:
                await interaction.followup.send(f"❌ Не удалось перемотать вперед на {seek_time}с.", ephemeral=True)
        except discord.errors.NotFound:
            logger.warning("Взаимодействие истекло или сообщение удалено")
        except Exception as e:
            logger.error(f"Ошибка в кнопке перемотки вперед: {e}")

    @discord.ui.button(emoji="📋", style=discord.ButtonStyle.secondary, custom_id="queue", row=1)
    async def queue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Кнопка показа очереди."""
        await interaction.response.defer()

        queue_info = self.player.get_queue_info()

        if not queue_info['tracks']:
            await interaction.followup.send("❌ Очередь пуста.", ephemeral=True)
            return

        embed = discord.Embed(
            title="📋 Очередь треков",
            description=f"Всего треков: {queue_info['total']}",
            color=discord.Color.green()
        )

        for i, track in enumerate(queue_info['tracks'][:10]):
            prefix = "▶️ " if i == queue_info['current_index'] else ""
            duration = music_service.format_duration(track["duration"])
            embed.add_field(
                name=f"{prefix}{i + 1}. {track['title'][:100]}",
                value=f"{track['uploader']} | {duration}",
                inline=False
            )

        if queue_info['total'] > 10:
            embed.set_footer(text=f"... и еще {queue_info['total'] - 10} треков")

        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(emoji="🔂", style=discord.ButtonStyle.secondary, custom_id="loop_track", row=2)
    async def loop_track_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Кнопка зацикливания текущего трека."""
        await interaction.response.defer()
        
        mode = self.player.toggle_loop_track()
        
        # Обновить стиль кнопки
        button.style = discord.ButtonStyle.success if mode == LoopMode.TRACK else discord.ButtonStyle.secondary
        
        # Если включили зацикливание трека, отключить зацикливание плейлиста
        if mode == LoopMode.TRACK:
            for item in self.children:
                if isinstance(item, discord.ui.Button) and item.custom_id == "loop_playlist":
                    item.style = discord.ButtonStyle.secondary
        
        await self._update_player_message()
        
        status = "включено" if mode == LoopMode.TRACK else "выключено"
        await interaction.followup.send(f"🔂 Зацикливание трека {status}.", ephemeral=True)

    @discord.ui.button(emoji="🔁", style=discord.ButtonStyle.secondary, custom_id="loop_playlist", row=2)
    async def loop_playlist_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Кнопка зацикливания плейлиста."""
        await interaction.response.defer()
        
        mode = self.player.toggle_loop_playlist()
        
        # Обновить стиль кнопки
        button.style = discord.ButtonStyle.success if mode == LoopMode.PLAYLIST else discord.ButtonStyle.secondary
        
        # Если включили зацикливание плейлиста, отключить зацикливание трека
        if mode == LoopMode.PLAYLIST:
            for item in self.children:
                if isinstance(item, discord.ui.Button) and item.custom_id == "loop_track":
                    item.style = discord.ButtonStyle.secondary
        
        await self._update_player_message()
        
        status = "включено" if mode == LoopMode.PLAYLIST else "выключено"
        await interaction.followup.send(f"🔁 Зацикливание плейлиста {status}.", ephemeral=True)


    async def _update_player_message(self):
        """Обновление сообщения проигрывателя."""
        if not self.message or not self.player.current_track:
            return

        embed = self._create_player_embed()
        
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                if item.custom_id == "pause_resume":
                    item.emoji = "▶️" if self.player.is_paused else "⏸️"
                elif item.custom_id == "loop_track":
                    item.style = discord.ButtonStyle.success if self.player.loop_mode == LoopMode.TRACK else discord.ButtonStyle.secondary
                elif item.custom_id == "loop_playlist":
                    item.style = discord.ButtonStyle.success if self.player.loop_mode == LoopMode.PLAYLIST else discord.ButtonStyle.secondary

        
        try:
            await self.message.edit(embed=embed, view=self)
        except Exception as e:
            logger.error(f"Ошибка обновления проигрывателя: {e}")

    def _create_player_embed(self) -> discord.Embed:
        """
        Создание embed для проигрывателя.
        
        Returns:
            Discord Embed с информацией о текущем треке
        """
        track = self.player.current_track
        if not track:
            return discord.Embed(
                title="🎵 Проигрыватель", 
                description="Нет активного трека",
                color=0x9B59B6
            )

        duration = music_service.format_duration(track["duration"])
        queue_info = self.player.get_queue_info()
        position, total_duration = self.player.get_playback_position()
        embed = discord.Embed(
            title="🎵 Сейчас играет",
            description=f"**[{track['title']}]({track['url']})**",
            color=0x9B59B6,
            url=track['url']
        )
        embed.add_field(name="Канал", value=track['uploader'], inline=True)
        embed.add_field(name="Длительность", value=duration, inline=True)

        if track.get('thumbnail'):
            embed.set_thumbnail(url=track['thumbnail'])

        status_emoji = "⏸️" if self.player.is_paused else "▶️"
        status_text = "На паузе" if self.player.is_paused else "Воспроизводится"
        embed.add_field(name="Статус", value=f"{status_emoji} {status_text}", inline=False)

        if total_duration > 0:
            progress = position / total_duration
            bar_length = 15
            filled = max(0, int(bar_length * progress))

            if filled == 0:
                bar = "○" + "─" * (bar_length - 1)
            elif filled >= bar_length:
                bar = "─" * (bar_length - 1) + "●"
            else:
                bar = "─" * (filled - 1) + "●" + "─" * (bar_length - filled)
            
            position_str = music_service.format_duration(position)
            total_str = music_service.format_duration(total_duration)
            progress_text = f"`{position_str}` {bar} `{total_str}`"
            embed.add_field(name="⏳ Прогресс", value=progress_text, inline=False)

        # Отображение режима зацикливания
        if self.player.loop_mode == LoopMode.TRACK:
            embed.add_field(name="🔂 Режим", value="Зацикливание трека", inline=True)
        elif self.player.loop_mode == LoopMode.PLAYLIST:
            embed.add_field(name="🔁 Режим", value="Зацикливание плейлиста", inline=True)

        embed.set_footer(text=f"♫ Трек {queue_info['current_index'] + 1} из {queue_info['total']}")

        return embed
