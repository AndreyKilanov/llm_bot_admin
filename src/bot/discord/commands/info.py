"""Модуль информационных команд плеера.

Содержит команды для просмотра очереди, текста текущей песни и общей справки.
"""

import discord
from discord.ext import commands

from src.bot.discord.views import QueuePaginationView
from src.bot.discord.views.emoji_manager import emoji_manager
from src.bot.discord.views.constants import commands_config, ui_config
from src.services import lyrics_service
from .base import BaseMusicCog


class InfoCommands(BaseMusicCog):
    """Ког для информационных команд плеера (очередь, текст песни, помощь)."""

    @commands.hybrid_command(
        name=commands_config.queue.name, 
        description=commands_config.queue.description
    )
    async def queue_cmd(self, ctx: commands.Context) -> None:
        """Показать текущую очередь воспроизведения.

        Args:
            ctx: Контекст команды.
        """
        if not ctx.guild:
            return
            
        player = self.get_player(ctx.guild.id)
        if not player or not player.queue:
            await ctx.send(ui_config.msg_err_queue_empty, ephemeral=True)
            return
            
        view = QueuePaginationView(player, ctx, items_per_page=ui_config.items_per_page)
        await ctx.send(embed=view.create_embed(), view=view, ephemeral=True)

    @commands.hybrid_command(
        name=commands_config.lyrics.name, 
        description=commands_config.lyrics.description
    )
    async def lyrics_cmd(self, ctx: commands.Context) -> None:
        """Показать текст текущей песни.

        Args:
            ctx: Контекст команды.
        """
        if not ctx.guild:
            return
            
        player = self.get_player(ctx.guild.id)
        if not player or not player.current_track:
            await ctx.send(ui_config.msg_err_no_active_track, ephemeral=True)
            return

        await ctx.defer(ephemeral=True)
        track = player.current_track
        content = await lyrics_service.get_lyrics(track.title, track.uploader or "")
        
        if not content:
            await ctx.send(ui_config.msg_no_lyrics, ephemeral=True)
            return

        embed = discord.Embed(
            title=f"Текст песни: {track.title}",
            description=content,
            color=ui_config.embed_color
        )
        await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_command(
        name=commands_config.help.name, 
        description=commands_config.help.description
    )
    async def help_cmd(self, ctx: commands.Context) -> None:
        """Отображение справки по всем командам бота.

        Args:
            ctx: Контекст команды.
        """
        e = emoji_manager.get_all()
        embed = discord.Embed(
            title=f"{e.robot} LLM Bot — Справка",
            description=(
                f"Я — мультифункциональный бот с ИИ и музыкой! {e.sparkle}\n\n"
                "**🧠 Чат с ИИ**\n"
                "• Отвечаю в ЛС или по упоминанию `@Бот`.\n"
                "• Использую современные LLM для диалога.\n\n"
                "**🎵 Музыкальные команды**\n"
                f"• `/{commands_config.play.name}` — {commands_config.play.description}\n"
                f"• `/{commands_config.search.name}` — {commands_config.search.description}\n"
                f"• `/{commands_config.link.name}` — {commands_config.link.description}\n"
                f"• `/{commands_config.playlist.name}` — {commands_config.playlist.description}\n"
                f"• `/{commands_config.queue.name}` — {commands_config.queue.description}\n\n"
                "**🎮 Пульт управления**\n"
                f"{e.previous} — Назад | {e.play}{e.pause} — Пауза/Плей | {e.next} — Вперед\n"
                f"{e.stop_only} — Стоп | {e.queue} — Очередь | {e.shuffle} — Шатл | {e.repeat_all} — Цикл\n\n"
                "**⚙️ Быстрое управление**\n"
                f"• `/{commands_config.skip.name}` / `/{commands_config.previous.name}` — Навигация\n"
                f"• `/{commands_config.pause.name}` / `/{commands_config.resume.name}` — Состояние\n"
                f"• `/{commands_config.stop.name}` — {commands_config.stop.description}"
            ),
            color=discord.Color.from_rgb(88, 101, 242)
        )
        repo_url = "https://github.com/AndreyKilanov/llm_bot_admin/tree/main"
        embed.description += f"\n\n-# [{e.info} GitHub Repository]({repo_url})"
        await ctx.send(embed=embed)
