import asyncio
import logging
from typing import Optional

import discord
from discord import Message
from discord.ext import commands

from config import settings
from src.bot.discord.handlers import MessageHandler
from src.bot.discord.music_player import MusicPlayer
from src.bot.discord.views import MusicPlayerView, TrackSelectionView
from src.services.music_service import music_service

logger = logging.getLogger("discord.bot")


class DiscordBot:
    """Класс для управления Discord ботом."""
    
    def __init__(self):
        """Инициализация Discord бота."""
        intents = discord.Intents.default()
        intents.messages = True
        intents.guilds = True
        intents.message_content = True
        intents.dm_messages = True
        intents.voice_states = True

        self.bot = commands.Bot(command_prefix="/", intents=intents)
        self.bot.on_ready = self.on_ready
        self.bot.on_message = self.on_message
        self.music_players: dict[int, MusicPlayer] = {}
        self.message_handler = MessageHandler(self.bot)
        self._register_commands()
        self.bg_task: Optional[asyncio.Task] = None

    def _register_commands(self):
        """Регистрация всех музыкальных команд."""

        @self.bot.command(name="playmusic", help="Воспроизвести музыку из YouTube")
        async def playmusic(ctx: commands.Context, *, query: str):
            """Команда для поиска и воспроизведения музыки."""
            await self._handle_playmusic(ctx, query)

        @self.bot.command(name="skip", help="Переключить на следующий трек")
        async def skip(ctx: commands.Context):
            """Команда для переключения на следующий трек."""
            await self._handle_skip(ctx)

        @self.bot.command(name="previous", help="Вернуться к предыдущему треку")
        async def previous(ctx: commands.Context):
            """Команда для возврата к предыдущему треку."""
            await self._handle_previous(ctx)

        @self.bot.command(name="pause", help="Приостановить воспроизведение")
        async def pause(ctx: commands.Context):
            """Команда для паузы."""
            await self._handle_pause(ctx)

        @self.bot.command(name="resume", help="Возобновить воспроизведение")
        async def resume(ctx: commands.Context):
            """Команда для возобновления."""
            await self._handle_resume(ctx)

        @self.bot.command(name="stop", help="Остановить воспроизведение и очистить очередь")
        async def stop(ctx: commands.Context):
            """Команда для остановки."""
            await self._handle_stop(ctx)

        @self.bot.command(name="queue", help="Показать очередь треков")
        async def queue(ctx: commands.Context):
            """Команда для отображения очереди."""
            await self._handle_queue(ctx)

        @self.bot.command(name="nowplaying", help="Показать текущий трек")
        async def nowplaying(ctx: commands.Context):
            """Команда для отображения текущего трека."""
            await self._handle_nowplaying(ctx)

    async def start(self):
        """Запуск Discord бота."""
        if not discord.opus.is_loaded():
            try:
                discord.opus.load_opus("/usr/lib/x86_64-linux-gnu/libopus.so.0")
                logger.info("Opus loaded from /usr/lib/x86_64-linux-gnu/libopus.so.0")
            except Exception as e:
                logger.error(f"Failed to load Opus: {e}")
                logger.error("Voice will NOT work! Install libopus0 in your Docker image.")
        else:
            logger.info("Opus already loaded.")

        token = settings.DISCORD_BOT_TOKEN
        if token:
            token = token.strip().strip('"').strip("'")

        if not token or token.lower() in ("none", "your_token_here", ""):
            logger.warning("Discord token не указан или имеет недопустимое значение. Discord бот не будет запущен.")
            return

        logger.info("Starting Discord bot...")
        try:
            await self.bot.start(token)
        except Exception as e:
            logger.error(f"Failed to start Discord bot: {e}")

    async def stop(self):
        """Остановка Discord бота."""
        for player in self.music_players.values():
            await player.disconnect()

        if self.bot:
            await self.bot.close()

    async def on_ready(self):
        """Обработчик события готовности бота."""
        logger.info(f"Discord Bot connected as {self.bot.user}")

    async def on_message(self, message: Message):
        """
        Обработчик входящих сообщений.
        
        Args:
            message: Входящее сообщение
        """
        await self.bot.process_commands(message)
        await self.message_handler.handle_message(message)

    # ==================== Музыкальные команды ====================

    def _get_or_create_player(self, guild_id: int) -> MusicPlayer:
        """
        Получить или создать музыкальный плеер для сервера.
        
        Args:
            guild_id: ID сервера Discord
            
        Returns:
            Экземпляр MusicPlayer
        """
        if guild_id not in self.music_players:
            self.music_players[guild_id] = MusicPlayer(guild_id, self.bot)
        return self.music_players[guild_id]

    async def _handle_playmusic(self, ctx: commands.Context, query: str):
        """Обработка команды /playmusic."""
        if not ctx.author.voice:
            await ctx.send("❌ Вы должны находиться в голосовом канале!")
            return

        voice_channel = ctx.author.voice.channel

        await ctx.send(f"🔍 Поиск: **{query}**...")

        tracks = await music_service.search_tracks(query, max_results=5)

        if not tracks:
            await ctx.send("❌ Треки не найдены.")
            return

        player = self._get_or_create_player(ctx.guild.id)
        player.set_text_channel(ctx.channel)
        player._voice_channel = voice_channel

        if len(tracks) == 1:
            player.add_to_queue(tracks)

            if not player.is_playing:
                await player.play_from_start()

            await self._send_player_ui(ctx, player)
            return

        embed = discord.Embed(
            title="🎵 Найденные треки",
            description="Выберите трек, нажав на соответствующую кнопку:",
            color=discord.Color.blue()
        )

        for i, track in enumerate(tracks, 1):
            duration = music_service.format_duration(track["duration"])
            embed.add_field(
                name=f"{i}. {track['title'][:100]}",
                value=f"Канал: {track['uploader']} | {duration}",
                inline=False
            )

        view = TrackSelectionView(tracks, player, ctx)
        message = await ctx.send(embed=embed, view=view)
        view.message = message

    async def _handle_skip(self, ctx: commands.Context):
        """Обработка команды /skip."""
        player = self.music_players.get(ctx.guild.id)

        if not player or not player.is_playing:
            await ctx.send("❌ Ничего не воспроизводится.")
            return

        if await player.play_next():
            await ctx.send("⏭️ Переключено на следующий трек.")
        else:
            await ctx.send("❌ Это последний трек в очереди.")

    async def _handle_previous(self, ctx: commands.Context):
        """Обработка команды /previous."""
        player = self.music_players.get(ctx.guild.id)

        if not player or not player.is_playing:
            await ctx.send("❌ Ничего не воспроизводится.")
            return

        if await player.play_previous():
            await ctx.send("⏮️ Возврат к предыдущему треку.")
        else:
            await ctx.send("❌ Это первый трек в очереди.")

    async def _handle_pause(self, ctx: commands.Context):
        """Обработка команды /pause."""
        player = self.music_players.get(ctx.guild.id)

        if not player or not player.is_playing:
            await ctx.send("❌ Ничего не воспроизводится.")
            return

        if player.pause():
            await ctx.send("⏸️ Воспроизведение приостановлено.")
        else:
            await ctx.send("❌ Не удалось приостановить воспроизведение.")

    async def _handle_resume(self, ctx: commands.Context):
        """Обработка команды /resume."""
        player = self.music_players.get(ctx.guild.id)

        if not player:
            await ctx.send("❌ Плеер не найден.")
            return

        if player.resume():
            await ctx.send("▶️ Воспроизведение возобновлено.")
        else:
            await ctx.send("❌ Воспроизведение не было приостановлено.")

    async def _handle_stop(self, ctx: commands.Context):
        """Обработка команды /stop."""
        player = self.music_players.get(ctx.guild.id)

        if not player:
            await ctx.send("❌ Плеер не найден.")
            return

        await player.stop()
        await player.disconnect()
        del self.music_players[ctx.guild.id]
        await ctx.send("⏹️ Воспроизведение остановлено, бот отключен от канала.")

    async def _handle_queue(self, ctx: commands.Context):
        """Обработка команды /queue."""
        player = self.music_players.get(ctx.guild.id)

        if not player or not player.queue:
            await ctx.send("❌ Очередь пуста.")
            return

        queue_info = player.get_queue_info()
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

        await ctx.send(embed=embed)

    async def _handle_nowplaying(self, ctx: commands.Context):
        """Обработка команды /nowplaying."""
        player = self.music_players.get(ctx.guild.id)

        if not player or not player.current_track:
            await ctx.send("❌ Ничего не воспроизводится.")
            return

        track = player.current_track
        duration = music_service.format_duration(track["duration"])
        embed = discord.Embed(
            title="🎵 Сейчас играет",
            description=f"**{track['title']}**",
            color=discord.Color.purple()
        )
        embed.add_field(name="Канал", value=track['uploader'], inline=True)
        embed.add_field(name="Длительность", value=duration, inline=True)

        if track.get('thumbnail'):
            embed.set_thumbnail(url=track['thumbnail'])

        status = "⏸️ Пауза" if player.is_paused else "▶️ Воспроизводится"
        embed.add_field(name="Статус", value=status, inline=False)
        queue_info = player.get_queue_info()
        embed.set_footer(text=f"Трек {queue_info['current_index'] + 1} из {queue_info['total']}")

        await ctx.send(embed=embed)

    async def _send_player_ui(self, ctx: commands.Context, player: MusicPlayer):
        """
        Создание и отправка постоянного проигрывателя.
        
        Args:
            ctx: Контекст команды
            player: Экземпляр MusicPlayer
        """
        if not player.current_track:
            return

        player_view = MusicPlayerView(player, ctx)
        embed = player_view._create_player_embed()
        message = await ctx.send(embed=embed, view=player_view)
        player.player_view = player_view
        player.player_message = message
        player_view.message = message
        await player_view.start_auto_update()

discord_bot = DiscordBot()
