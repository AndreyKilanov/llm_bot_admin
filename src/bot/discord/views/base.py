from typing import TYPE_CHECKING, Any
import discord
from discord.ext import commands

from .constants import EMOJI_ERROR

if TYPE_CHECKING:
    from src.bot.discord.player import MusicPlayer

type TrackInfo = dict[str, Any]
type DiscordEmoji = discord.Emoji | discord.PartialEmoji | str


class BaseMusicView(discord.ui.View):
    """Базовый класс для всех музыкальных View с общими методами."""

    def __init__(self, timeout: float | None = None):
        """Инициализация базового View.

        Args:
            timeout: Время ожидания взаимодействия в секундах.
        """
        super().__init__(timeout=timeout)

    async def _verify_voice_connection(
        self, 
        interaction: discord.Interaction, 
        player: "MusicPlayer", 
        ctx: commands.Context
    ) -> bool:
        """Проверяет наличие автора в голосовом канале и подключает плеер.

        Args:
            interaction: Объект взаимодействия Discord.
            player: Экземпляр музыкального плеера.
            ctx: Контекст команды.

        Returns:
            True, если подключение успешно, иначе False.
        """
        if not ctx.author.voice:
            await interaction.response.send_message(
                f"{EMOJI_ERROR} Вы больше не в голосовом канале!",
                ephemeral=True
            )
            return False

        if not await player.connect(ctx.author.voice.channel):
            await interaction.followup.send(
                f"{EMOJI_ERROR} Не удалось подключиться к голосовому каналу.",
                ephemeral=True
            )
            return False

        return True

    async def _handle_playback_start(self, player: "MusicPlayer", ctx: commands.Context):
        """Запускает воспроизведение и создает View плеера, если нужно.

        Args:
            player: Экземпляр музыкального плеера.
            ctx: Контекст команды.
        """
        from .music_player import MusicPlayerView

        if not player.is_playing:
            await player.play_from_start()

        if player.current_track:
            player_view = MusicPlayerView(player, ctx)
            embed = player_view.create_player_embed()
            message = await ctx.send(embed=embed, view=player_view)

            player.player_view = player_view
            player.player_message = message
            player_view.message = message

            await player_view.start_auto_update()
