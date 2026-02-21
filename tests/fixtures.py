import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram.types import Message, User, Chat
from src.bot.discord.music_player import MusicPlayer
import discord

# --- Discord Mocks ---

class FakeGuild:
    def __init__(self, guild_id):
        self.id = guild_id
        self.name = f"Guild {guild_id}"
        self.voice_client = None

class FakeVoiceClient:
    def __init__(self, guild_id):
        self.guild = FakeGuild(guild_id)
        self.guild.voice_client = self
        self.channel = None
        self.is_playing_status = False
        self.is_paused_status = False
        self.stop_called = 0
        self.pause_called = 0
        self.resume_called = 0
        self.disconnect_called = 0

    def is_playing(self):
        return self.is_playing_status

    def is_paused(self):
        return self.is_paused_status
        
    def is_connected(self):
        return True

    def stop(self):
        self.stop_called += 1

    def play(self, source, *, after=None):
        self.is_playing_status = True
        self._after = after
        return None

    def pause(self):
        self.pause_called += 1
        self.is_paused_status = True
        self.is_playing_status = False

    def resume(self):
        self.resume_called += 1
        self.is_paused_status = False
        self.is_playing_status = True

    async def disconnect(self, *args, **kwargs):
        self.disconnect_called += 1

class FakeVoiceChannel:
    def __init__(self):
        self.id = 456
        self.name = "Test Channel"
        self.connect_called = 0
        self.fake_vc = None

    async def connect(self, *args, **kwargs):
        self.connect_called += 1
        return self.fake_vc

class FakeBot:
    def __init__(self):
        self.voice_clients = []
        self.mock_guild = FakeGuild(123)
        self.user = MagicMock(id=999, name="TestBot")
        
    def get_guild(self, guild_id):
        if guild_id == 123:
            return self.mock_guild
        return None

@pytest.fixture
def mock_bot_fake():
    return FakeBot()

@pytest.fixture
def mock_voice_channel():
    return FakeVoiceChannel()

@pytest.fixture
def discord_player(mock_bot_fake):
    return MusicPlayer(guild_id=123, bot=mock_bot_fake)

class DiscordMockContext:
    def __init__(self):
        self.bot = MagicMock()
        self.guild = MagicMock()
        self.guild.id = 123
        self.author = MagicMock()
        self.author.voice = MagicMock()
        self.author.voice.channel = MagicMock()
        self.channel = MagicMock()
        self.send = AsyncMock()

@pytest.fixture
def mock_discord_ctx():
    return DiscordMockContext()

class AsyncContextManagerMock:
    async def __aenter__(self): return self
    async def __aexit__(self, *args): pass

@pytest.fixture
def mock_discord_message():
    msg = AsyncMock()
    msg.author = MagicMock(name="User")
    msg.author.id = 123
    msg.author.name = "test_user"
    msg.channel = MagicMock()
    msg.channel.id = 456
    msg.channel.name = "general"
    msg.channel.send = AsyncMock()
    msg.channel.typing = MagicMock(return_value=AsyncContextManagerMock())
    msg.guild = MagicMock()
    msg.guild.id = 789
    msg.guild.name = "Test Guild"
    msg.guild.me = MagicMock()
    msg.guild.me.nick = "TestBotNick"
    msg.content = "Hello bot"
    msg.clean_content = "Hello bot"
    msg.mentions = []
    return msg

# --- Telegram (Aiogram) Mocks ---

@pytest.fixture
def mock_tg_message():
    msg = AsyncMock()
    msg.from_user = MagicMock()
    msg.from_user.id = 123
    msg.from_user.username = "testuser"
    msg.chat = MagicMock()
    msg.chat.id = 456
    msg.chat.type = "private"
    msg.text = "Hello world"
    msg.reply_to_message = None
    msg.bot = AsyncMock()
    msg.bot.get_me.return_value = MagicMock(id=999, username="test_bot")
    msg.answer = AsyncMock()
    return msg
