import pytest

def test_lazy_imports():
    # To test __getattr__ we import the module and access attributes
    import src.bot as bot
    
    # Telegram
    assert bot.router is not None
    assert bot.LoggingMiddleware is not None
    assert bot.WhitelistMiddleware is not None
    
    # Discord
    assert bot.DiscordBot is not None
    assert bot.discord_bot is not None
    
    # Invalid
    with pytest.raises(AttributeError):
        _ = bot.NonExistentComponent
