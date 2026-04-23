from typing import TYPE_CHECKING, Any, TypeAlias, Union
import asyncio
import logging
import discord
from discord.ext import commands

from .constants import ui_config
from .emoji_manager import emoji_manager
from src.services import SettingsService
from src.bot.discord.player import PlayerFactory

if TYPE_CHECKING:
    from src.bot.discord.player import MusicPlayer

TrackInfo: TypeAlias = dict[str, Any]
DiscordEmoji: TypeAlias = discord.Emoji | discord.PartialEmoji | str


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
        ctx: Union[commands.Context, discord.Interaction]
    ) -> bool:
        """Проверяет наличие автора в голосовом канале и подключает плеер.

        Args:
            interaction: Объект взаимодействия Discord.
            player: Экземпляр музыкального плеера.
            ctx: Контекст команды или Interaction.

        Returns:
            True, если подключение успешно, иначе False.
        """
        e = emoji_manager.get_all()
        user = ctx.author if isinstance(ctx, commands.Context) else ctx.user
        if not user.voice:
            await interaction.response.send_message(
                f"{e.error} {ui_config.msg_err_not_in_voice}",
                ephemeral=True
            )
            return False

        if not await player.connect(user.voice.channel):
            await interaction.followup.send(
                f"{e.error} {ui_config.msg_conn_fail}",
                ephemeral=True
            )
            return False

        return True

    async def _handle_playback_start(self, player: "MusicPlayer", ctx: Union[commands.Context, discord.Interaction]):
        """Запускает воспроизведение и создает View плеера, если нужно.

        Args:
            player: Экземпляр музыкального плеера.
            ctx: Контекст команды или Interaction.
        """
        from .music_player import MusicPlayerView

        if not player.is_playing:
            await player.play_from_start()

        await player.clear_player_ui()

        if player.current_track:
            player_view = MusicPlayerView(player, ctx)
            embed = player_view.create_player_embed()
            
            if isinstance(ctx, commands.Context):
                message = await ctx.send(embed=embed, view=player_view)
            else:
                if ctx.response.is_done():
                    message = await ctx.followup.send(embed=embed, view=player_view)
                else:
                    await ctx.response.send_message(embed=embed, view=player_view)
                    message = await ctx.original_response()

            player.player_view = player_view
            player.player_message = message
            player_view.message = message

            await player_view.start_auto_update()

    async def _delete_with_delay(self, message: Union[discord.Message, discord.WebhookMessage, None], delay: float) -> None:
        """Безопасно удаляет сообщение через указанную задержку."""
        if not message:
            return

        async def delayed_delete():
            await asyncio.sleep(delay)
            try:
                await message.delete()
            except (discord.NotFound, discord.Forbidden, discord.HTTPException, TypeError):
                pass
        
        asyncio.create_task(delayed_delete())

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item) -> None:
        """Обработка ошибок при взаимодействии с компонентами View.
        
        Отправляет эфемерное сообщение об ошибке и логирует исключение.
        """
        logging.getLogger("discord.views").error(f"Ошибка в {self.__class__.__name__} при нажатии {item}: {error}", exc_info=error)
        
        e = emoji_manager.get_all()
        msg_text = f"{e.error} {ui_config.msg_error}"
        
        try:
            if interaction.response.is_done():
                msg = await interaction.followup.send(msg_text, ephemeral=True)
                await self._delete_with_delay(msg, 10)
            else:
                await interaction.response.send_message(msg_text, ephemeral=True)
                msg = await interaction.original_response()
                await self._delete_with_delay(msg, 10)
        except (discord.HTTPException, discord.InteractionResponded):
            pass

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Проверяет, разрешено ли взаимодействие с компонентами View.
        
        Если бот выключен в админке, выводит предупреждение и останавливает плеер.
        """
        if not await SettingsService.is_discord_bot_enabled():
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    ui_config.msg_bot_disabled, 
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    ui_config.msg_bot_disabled, 
                    ephemeral=True
                )
            
            # Если бот выключен, но плеер играет, останавливаем его
            if interaction.guild_id:
                player = PlayerFactory.get_player(interaction.guild_id, interaction.client)
                if player and player.is_connected:
                    await player.disconnect()
            return False
            
        return True
