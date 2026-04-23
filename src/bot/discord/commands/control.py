"""Модуль команд управления воспроизведением.

Отвечает за постановку на паузу, пропуск треков, и остановку плеера.
"""

from discord.ext import commands

from src.bot.discord.views.emoji_manager import emoji_manager
from src.bot.discord.views.constants import commands_config, ui_config
from .base import BaseMusicCog


class ControlCommands(BaseMusicCog):
    """Ког для управления состоянием музыкального плеера (пауза, стоп, пропуск)."""

    @commands.hybrid_command(
        name=commands_config.skip.name, 
        description=commands_config.skip.description
    )
    async def skip_cmd(self, ctx: commands.Context) -> None:
        """Пропуск текущего трека.

        Args:
            ctx: Контекст команды.
        """
        if not await self.verify_ready(ctx):
            return
        
        if not ctx.guild:
            return
            
        player = self.get_player(ctx.guild.id)
        e = emoji_manager.get_all()
        if not player or not player.is_playing:
            await ctx.send(ui_config.msg_nothing_playing, ephemeral=True)
            return
            
        if await player.play_next():
            await ctx.send(f"{e.next} Следующий трек.")
        else:
            await ctx.send(f"{e.error} Очередь окончена.")

    @commands.hybrid_command(
        name=commands_config.previous.name, 
        description=commands_config.previous.description
    )
    async def previous_cmd(self, ctx: commands.Context) -> None:
        """Возврат к предыдущему треку.

        Args:
            ctx: Контекст команды.
        """
        if not await self.verify_ready(ctx):
            return
            
        if not ctx.guild:
            return
            
        player = self.get_player(ctx.guild.id)
        e = emoji_manager.get_all()
        if not player or not player.is_playing:
            await ctx.send(ui_config.msg_nothing_playing, ephemeral=True)
            return
            
        if await player.play_previous():
            await ctx.send(f"{e.previous} Предыдущий трек.")
        else:
            await ctx.send(f"{e.error} Это первый трек.")

    @commands.hybrid_command(
        name=commands_config.pause.name, 
        description=commands_config.pause.description
    )
    async def pause_cmd(self, ctx: commands.Context) -> None:
        """Постановка воспроизведения на паузу.

        Args:
            ctx: Контекст команды.
        """
        if not await self.verify_ready(ctx):
            return
            
        if not ctx.guild:
            return
            
        player = self.get_player(ctx.guild.id)
        e = emoji_manager.get_all()
        if not player or not player.is_playing:
            await ctx.send(ui_config.msg_nothing_playing, ephemeral=True)
            return
            
        if player.pause():
            await ctx.send(f"{e.pause} Музыка на паузе.")
        else:
            await ctx.send(f"{e.error} Ошибка при попытке паузы.")

    @commands.hybrid_command(
        name=commands_config.resume.name, 
        description=commands_config.resume.description
    )
    async def resume_cmd(self, ctx: commands.Context) -> None:
        """Возобновление воспроизведения.

        Args:
            ctx: Контекст команды.
        """
        if not await self.verify_ready(ctx):
            return
            
        if not ctx.guild:
            return
            
        player = self.get_player(ctx.guild.id)
        e = emoji_manager.get_all()
        if not player:
            await ctx.send(ui_config.msg_player_missing, ephemeral=True)
            return
            
        if player.resume():
            await ctx.send(f"{e.play} Продолжаем воспроизведение.")
        else:
            await ctx.send(f"{e.error} Плеер был активен.")

    @commands.hybrid_command(
        name=commands_config.stop.name, 
        description=commands_config.stop.description
    )
    async def stop_cmd(self, ctx: commands.Context) -> None:
        """Полная остановка плеера и выход из канала.

        Args:
            ctx: Контекст команды.
        """
        if not await self.verify_ready(ctx):
            return
            
        if not ctx.guild:
            return
            
        player = self.get_player(ctx.guild.id)
        if not player or not player.is_playing:
            await ctx.send(ui_config.msg_nothing_playing, ephemeral=True)
            return
            
        await player.stop()
        e = emoji_manager.get_all()
        await ctx.send(f"{e.stop_only} Остановка и выход.")
