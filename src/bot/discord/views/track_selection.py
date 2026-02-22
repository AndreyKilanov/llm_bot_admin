from typing import TYPE_CHECKING
import discord
from discord.ext import commands

from .base import BaseMusicView, TrackInfo
from .constants import (
    DEFAULT_VIEW_TIMEOUT, 
    EMOJI_SUCCESS, 
    EMOJI_TIMEOUT
)

if TYPE_CHECKING:
    from src.bot.discord.player import MusicPlayer


class TrackSelectionView(BaseMusicView):
    """View для выбора трека из списка результатов поиска."""

    def __init__(self, tracks: list[TrackInfo], player: "MusicPlayer", ctx: commands.Context):
        """Инициализация View выбора трека.

        Args:
            tracks: Список найденных треков.
            player: Экземпляр MusicPlayer.
            ctx: Контекст команды.
        """
        super().__init__(timeout=DEFAULT_VIEW_TIMEOUT)
        self.tracks = tracks
        self.player = player
        self.ctx = ctx
        self.message: discord.Message | None = None

        self._build_buttons()

    def _build_buttons(self):
        """Создает кнопки выбора треков и кнопку 'Добавить все'."""
        for i in range(min(len(self.tracks), 5)):
            index = i
            button = discord.ui.Button(
                label=f"{i + 1}",
                style=discord.ButtonStyle.primary,
                custom_id=f"track_{i + 1}"
            )

            async def callback(interaction: discord.Interaction, idx=index):
                await self._select_track(interaction, idx)

            button.callback = callback
            self.add_item(button)

        add_all_btn = discord.ui.Button(
            label="Добавить все",
            style=discord.ButtonStyle.success,
            custom_id="add_all"
        )
        add_all_btn.callback = self._add_all_callback
        self.add_item(add_all_btn)

    async def _select_track(self, interaction: discord.Interaction, index: int):
        """Обработка выбора конкретного трека.

        Args:
            interaction: Объект взаимодействия.
            index: Индекс выбранного трека.
        """
        await interaction.response.defer()
        if not await self._verify_voice_connection(interaction, self.player, self.ctx):
            return

        track = self.tracks[index]
        self.player.add_to_queue([track])

        await interaction.edit_original_response(
            content=f"{EMOJI_SUCCESS} Трек добавлен в очередь!",
            embed=None,
            view=None
        )

        await self._handle_playback_start(self.player, self.ctx)
        self.stop()

    async def _add_all_callback(self, interaction: discord.Interaction):
        """Callback для кнопки 'Добавить все'."""
        await interaction.response.defer()
        if not await self._verify_voice_connection(interaction, self.player, self.ctx):
            return

        self.player.add_to_queue(self.tracks)

        await interaction.edit_original_response(
            content=f"{EMOJI_SUCCESS} Добавлено {len(self.tracks)} треков в очередь!",
            embed=None,
            view=None
        )

        await self._handle_playback_start(self.player, self.ctx)
        self.stop()

    async def on_timeout(self):
        """Обработка истечения времени ожидания."""
        if self.message:
            try:
                await self.message.edit(
                    content=f"{EMOJI_TIMEOUT} Время выбора истекло.",
                    embed=None,
                    view=None
                )
            except Exception:
                pass
