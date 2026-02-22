from typing import TYPE_CHECKING, Final

import discord
from discord.ext import commands

from src.services import music_service

from .base import BaseMusicView
from .constants import (
    DEFAULT_ITEMS_PER_PAGE,
    DEFAULT_VIEW_TIMEOUT,
    EMOJI_PLAY,
    LABEL_NEXT_PAGE,
    LABEL_PREV_PAGE,
    MSG_QUEUE_TITLE,
    MSG_QUEUE_TOTAL,
    MSG_QUEUE_EMPTY,
    MSG_QUEUE_FOOTER,
    MSG_TRACK_INFO,
    MSG_UNKNOWN,
)

if TYPE_CHECKING:
    from src.bot.discord.player import MusicPlayer


ID_PREV_PAGE: Final[str] = "queue_prev"
ID_NEXT_PAGE: Final[str] = "queue_next"


class QueuePaginationView(BaseMusicView):
    """View для отображения очереди с пагинацией.

    Attributes:
        player: Экземпляр музыкального плеера.
        ctx: Контекст команды.
        items_per_page: Количество треков на одной странице.
        current_page: Индекс текущей страницы.
        message: Сообщение с View.
    """

    def __init__(
        self,
        player: "MusicPlayer",
        ctx: commands.Context,
        items_per_page: int = DEFAULT_ITEMS_PER_PAGE,
    ) -> None:
        """Инициализация пагинации очереди.

        Args:
            player: Экземпляр MusicPlayer.
            ctx: Контекст команды.
            items_per_page: Количество треков на страницу. По умолчанию 5.
        """
        super().__init__(timeout=DEFAULT_VIEW_TIMEOUT)
        self.player: "MusicPlayer" = player
        self.ctx: commands.Context = ctx
        self.items_per_page: int = items_per_page
        self.current_page: int = 0
        self.message: discord.Message | None = None

        self._update_buttons()

    @property
    def total_pages(self) -> int:
        """Общее количество страниц.

        Returns:
            int: Число страниц (минимум 1).
        """
        if not self.player.queue:
            return 1
        return max(
            1, (len(self.player.queue) + self.items_per_page - 1) // self.items_per_page
        )

    def _update_buttons(self) -> None:
        """Обновляет состояние кнопок в зависимости от текущей страницы."""
        self.prev_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= self.total_pages - 1

    def create_embed(self) -> discord.Embed:
        """Создает Embed для текущей страницы.

        Returns:
            discord.Embed: Сформированный Embed очереди.
        """
        embed = discord.Embed(
            title=MSG_QUEUE_TITLE,
            description=MSG_QUEUE_TOTAL.format(total=len(self.player.queue)),
            color=discord.Color.green(),
        )

        if not self.player.queue:
            embed.description = MSG_QUEUE_EMPTY
            return embed

        start_idx = self.current_page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_tracks = self.player.queue[start_idx:end_idx]

        for i, track in enumerate(page_tracks, start=start_idx):
            is_current = i == self.player.current_index
            prefix = f"{EMOJI_PLAY} " if is_current else ""
            duration = music_service.format_duration(track.get("duration", 0))

            title = track.get("title", MSG_UNKNOWN)[:100]
            uploader = track.get("uploader", MSG_UNKNOWN)

            embed.add_field(
                name=f"{prefix}{i + 1}. {title}",
                value=MSG_TRACK_INFO.format(uploader=uploader, duration=duration),
                inline=False,
            )

        embed.set_footer(
            text=MSG_QUEUE_FOOTER.format(
                current=self.current_page + 1,
                pages=self.total_pages
            )
        )
        return embed

    @discord.ui.button(
        label=LABEL_PREV_PAGE,
        style=discord.ButtonStyle.secondary,
        custom_id=ID_PREV_PAGE,
    )
    async def prev_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        """Переход на предыдущую страницу.

        Args:
            interaction: Объект взаимодействия.
            button: Нажатая кнопка.
        """
        await interaction.response.defer()
        if self.current_page > 0:
            self.current_page -= 1
            self._update_buttons()
            await interaction.edit_original_response(
                embed=self.create_embed(), view=self
            )

    @discord.ui.button(
        label=LABEL_NEXT_PAGE,
        style=discord.ButtonStyle.secondary,
        custom_id=ID_NEXT_PAGE,
    )
    async def next_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        """Переход на следующую страницу.

        Args:
            interaction: Объект взаимодействия.
            button: Нажатая кнопка.
        """
        await interaction.response.defer()
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self._update_buttons()
            await interaction.edit_original_response(
                embed=self.create_embed(), view=self
            )

    async def on_timeout(self) -> None:
        """При истечении времени убираем кнопки."""
        if self.message:
            for child in self.children:
                if isinstance(child, discord.ui.Button):
                    child.disabled = True
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass
