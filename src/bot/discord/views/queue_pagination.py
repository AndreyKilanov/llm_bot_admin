from typing import TYPE_CHECKING, Final

import discord
from discord.ext import commands

from src.services import music_service

from .base import BaseMusicView
from .constants import ui_config
from .emoji_manager import emoji_manager

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
        items_per_page: int = ui_config.items_per_page,
    ) -> None:
        """Инициализация пагинации очереди.

        Args:
            player: Экземпляр MusicPlayer.
            ctx: Контекст команды.
            items_per_page: Количество треков на страницу. По умолчанию 10.
        """
        super().__init__(timeout=ui_config.default_view_timeout)
        self.player: "MusicPlayer" = player
        self.ctx: commands.Context = ctx
        self.items_per_page: int = items_per_page
        self.current_page: int = 0
        if self.player.queue:
            self.current_page = self.player.current_index // self.items_per_page
            
        self.message: discord.Message | None = None

        self._update_buttons()
        self._update_select_menu()

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

    async def _update_view(self, interaction: discord.Interaction) -> None:
        """Обновляет кнопки и выпадающий список во View."""
        self._update_buttons()
        self._update_select_menu()
        await interaction.edit_original_response(embed=self.create_embed(), view=self)

    def _update_buttons(self) -> None:
        """Обновляет состояние кнопок переключения страниц."""
        self.prev_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= self.total_pages - 1

    def _update_select_menu(self) -> None:
        """Обновляет или создает выпадающий список выбора треков."""
        for item in self.children:
            if isinstance(item, discord.ui.Select):
                self.remove_item(item)
                break

        if not self.player.queue:
            return

        start_idx = self.current_page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_tracks = self.player.queue[start_idx:end_idx]

        options = []
        total_tracks = len(self.player.queue)
        idx_width = len(str(total_tracks))

        for i, track in enumerate(page_tracks, start=start_idx):
            title = str(track.title or 'Unknown')[:80]
            uploader = str(track.uploader or 'Unknown')[:40]
            label = f"{i + 1:>{idx_width}}. {title}"
            description = uploader

            if i == self.player.current_index:
                label = f"▶ {label}"

            options.append(discord.SelectOption(
                label=label,
                description=description,
                value=str(i)
            ))

        if options:
            placeholder = f"{ui_config.placeholder_queue_select}{ui_config.invisible_spacer}"
            select = discord.ui.Select(
                placeholder=placeholder[:100],
                options=options,
                custom_id="queue_select"
            )
            select.callback = self._select_callback
            self.add_item(select)

    async def _select_callback(self, interaction: discord.Interaction) -> None:
        """Обработка выбора трека из выпадающего списка."""
        await interaction.response.defer()
        index = int(interaction.data["values"][0])
        
        if await self.player.play_at_index(index):
            await self._update_view(interaction)
        else:
            e = emoji_manager.get_all()
            await interaction.followup.send(f"{e.error} {ui_config.msg_err_play_fail}", ephemeral=True)

    def create_embed(self) -> discord.Embed:
        """Создает Embed для текущей страницы.

        Returns:
            discord.Embed: Сформированный Embed очереди.
        """
        embed = discord.Embed(
            title=ui_config.msg_queue_title,
            description=ui_config.msg_queue_desc.format(total=len(self.player.queue)),
            color=discord.Color.green(),
        )

        if not self.player.queue:
            embed.description = ui_config.msg_queue_empty
            return embed

        start_idx = self.current_page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_tracks = self.player.queue[start_idx:end_idx]

        total_tracks = len(self.player.queue)
        idx_width = len(str(total_tracks))

        e = emoji_manager.get_all()
        for i, track in enumerate(page_tracks, start=start_idx):
            is_current = i == self.player.current_index
            prefix = f"{e.play} " if is_current else ""
            duration = music_service.format_duration(track.duration or 0)
            title = str(track.title or ui_config.msg_unknown)[:80]
            uploader = track.uploader or ui_config.msg_unknown
            embed.add_field(
                name=f"{prefix}{i + 1:>{idx_width}}. {title}",
                value=f"{uploader} | {duration}",
                inline=False,
            )

        footer_text = ui_config.msg_player_footer.format(
            current=self.current_page + 1, 
            pages=self.total_pages
        )
        embed.set_footer(
            text=f"{footer_text}{ui_config.invisible_spacer}"
        )
        return embed

    @discord.ui.button(
        label=ui_config.label_prev_page,
        style=discord.ButtonStyle(ui_config.style_secondary),
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
            await self._update_view(interaction)

    @discord.ui.button(
        label=ui_config.label_next_page,
        style=discord.ButtonStyle(ui_config.style_secondary),
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
            await self._update_view(interaction)

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
