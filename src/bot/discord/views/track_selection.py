from typing import TYPE_CHECKING, Final

import discord
from discord.ext import commands

from src.services import music_service

from .base import BaseMusicView, TrackInfo
from .constants import (
    DEFAULT_ITEMS_PER_PAGE,
    DEFAULT_VIEW_TIMEOUT,
    LABEL_ADD_ALL,
    LABEL_NEXT_PAGE,
    LABEL_PREV_PAGE,
    SEARCH_COLOR,
    MSG_SEARCH_RESULTS_TITLE,
    MSG_SEARCH_RESULTS_DESC,
    MSG_UNKNOWN,
    MSG_TRACK_ADDED,
    MSG_TRACKS_ADDED,
    MSG_SELECTION_TIMEOUT,
    MSG_SEARCH_FOOTER,
    MSG_UPLOADER_INFO,
    INVISIBLE_SPACER,
)

if TYPE_CHECKING:
    from src.bot.discord.player import MusicPlayer

ID_SELECT_PREFIX: Final[str] = "track_"
ID_ADD_ALL: Final[str] = "add_all"
ID_SEARCH_PREV: Final[str] = "search_prev"
ID_SEARCH_NEXT: Final[str] = "search_next"


class TrackSelectionView(BaseMusicView):
    """View для выбора трека из списка результатов поиска.

    Attributes:
        tracks: Список найденных треков.
        player: Экземпляр музыкального плеера.
        ctx: Контекст команды.
        message: Сообщение с View.
        current_page: Индекс текущей страницы.
        items_per_page: Количество треков на одной странице.
    """

    def __init__(
        self,
        tracks: list[TrackInfo],
        player: "MusicPlayer",
        ctx: commands.Context,
        items_per_page: int = DEFAULT_ITEMS_PER_PAGE,
    ) -> None:
        """Инициализация View выбора трека.

        Args:
            tracks: Список найденных треков.
            player: Экземпляр MusicPlayer.
            ctx: Контекст команды.
            items_per_page: Количество треков на страницу. По умолчанию 5.
        """
        super().__init__(timeout=DEFAULT_VIEW_TIMEOUT)
        self.tracks: list[TrackInfo] = tracks
        self.player: "MusicPlayer" = player
        self.ctx: commands.Context = ctx
        self.message: discord.Message | None = None
        self.current_page: int = 0
        self.items_per_page: int = items_per_page

        self._build_buttons()

    @property
    def total_pages(self) -> int:
        """Общее количество страниц.

        Returns:
            int: Число страниц (минимум 1).
        """
        if not self.tracks:
            return 1
        return max(1, (len(self.tracks) + self.items_per_page - 1) // self.items_per_page)

    def _build_buttons(self) -> None:
        """Создает кнопки выбора треков, пагинации и 'Добавить все'."""
        self.clear_items()

        start_idx = self.current_page * self.items_per_page
        page_tracks = self.tracks[start_idx : start_idx + self.items_per_page]

        for i, _ in enumerate(page_tracks):
            index = start_idx + i
            button = discord.ui.Button(
                label=f"{i + 1}",
                style=discord.ButtonStyle.primary,
                custom_id=f"{ID_SELECT_PREFIX}{i + 1}",
            )

            async def callback(
                interaction: discord.Interaction,
                idx: int = index
            ) -> None:
                await self._select_track(interaction, idx)

            button.callback = callback
            self.add_item(button)

        add_all_btn = discord.ui.Button(
            label=LABEL_ADD_ALL,
            style=discord.ButtonStyle.success,
            custom_id=ID_ADD_ALL,
        )
        add_all_btn.callback = self._add_all_callback
        self.add_item(add_all_btn)

        if self.total_pages > 1:
            prev_btn = discord.ui.Button(
                label=LABEL_PREV_PAGE,
                style=discord.ButtonStyle.secondary,
                custom_id=ID_SEARCH_PREV,
                disabled=self.current_page == 0,
            )
            prev_btn.callback = self._prev_page_callback
            self.add_item(prev_btn)

            next_btn = discord.ui.Button(
                label=LABEL_NEXT_PAGE,
                style=discord.ButtonStyle.secondary,
                custom_id=ID_SEARCH_NEXT,
                disabled=self.current_page >= self.total_pages - 1,
            )
            next_btn.callback = self._next_page_callback
            self.add_item(next_btn)

    def create_embed(self) -> discord.Embed:
        """Создает Embed с результатами поиска для текущей страницы.

        Returns:
            discord.Embed: Сформированный Embed с результатами.
        """
        embed = discord.Embed(
            title=MSG_SEARCH_RESULTS_TITLE,
            description=MSG_SEARCH_RESULTS_DESC,
            color=SEARCH_COLOR,
        )

        start_idx = self.current_page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_tracks = self.tracks[start_idx:end_idx]

        total_tracks = len(self.tracks)
        idx_width = len(str(total_tracks))

        for i, track in enumerate(page_tracks, 1):
            duration = music_service.format_duration(track.get("duration") or 0)
            title = track.get("title", MSG_UNKNOWN)[:80]
            uploader = track.get("uploader", MSG_UNKNOWN)

            embed.add_field(
                name=f"{i + (self.current_page * self.items_per_page):>{idx_width}}. {title}",
                value=MSG_UPLOADER_INFO.format(uploader=uploader, duration=duration),
                inline=False,
            )

        embed.set_footer(
            text=f"{MSG_SEARCH_FOOTER.format(total=len(self.tracks), current=self.current_page + 1, pages=self.total_pages)}{INVISIBLE_SPACER}"
        )
        return embed

    async def _prev_page_callback(self, interaction: discord.Interaction) -> None:
        """Переход на предыдущую страницу результатов.

        Args:
            interaction: Объект взаимодействия.
        """
        await interaction.response.defer()
        if self.current_page > 0:
            self.current_page -= 1
            self._build_buttons()
            await interaction.edit_original_response(embed=self.create_embed(), view=self)

    async def _next_page_callback(self, interaction: discord.Interaction) -> None:
        """Переход на следующую страницу результатов.

        Args:
            interaction: Объект взаимодействия.
        """
        await interaction.response.defer()
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self._build_buttons()
            await interaction.edit_original_response(embed=self.create_embed(), view=self)

    async def _select_track(self, interaction: discord.Interaction, index: int) -> None:
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

        msg = await interaction.edit_original_response(
            content=MSG_TRACK_ADDED, embed=None, view=None
        )

        # Удаляем сообщение о добавлении через 10 секунд
        asyncio.create_task(self._delete_after(msg, 10.0))

        await self._handle_playback_start(self.player, self.ctx)
        self.stop()

    async def _add_all_callback(self, interaction: discord.Interaction) -> None:
        """Callback для кнопки 'Добавить все'.

        Args:
            interaction: Объект взаимодействия.
        """
        await interaction.response.defer()
        if not await self._verify_voice_connection(interaction, self.player, self.ctx):
            return

        self.player.add_to_queue(self.tracks)

        msg = await interaction.edit_original_response(
            content=MSG_TRACKS_ADDED.format(count=len(self.tracks)),
            embed=None,
            view=None,
        )

        # Удаляем сообщение о добавлении через 10 секунд
        asyncio.create_task(self._delete_after(msg, 10.0))

        await self._handle_playback_start(self.player, self.ctx)
        self.stop()

    async def _delete_after(self, message: discord.Message | discord.InteractionMessage, delay: float) -> None:
        """Вспомогательный метод для удаления сообщения через заданное время."""
        await asyncio.sleep(delay)
        try:
            await message.delete()
        except Exception:
            pass

    async def on_timeout(self) -> None:
        """Обработка истечения времени ожидания."""
        if self.message:
            try:
                for child in self.children:
                    if isinstance(child, discord.ui.Button):
                        child.disabled = True
                await self.message.edit(content=MSG_SELECTION_TIMEOUT, view=self)
            except discord.HTTPException:
                pass
