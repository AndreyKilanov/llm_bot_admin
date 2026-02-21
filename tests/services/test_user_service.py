import pytest
import bcrypt
from tortoise import Tortoise
from src.services.user_service import UserService
from src.database.models import User


@pytest.mark.asyncio
async def test_get_user_by_username():
    user = await UserService.create_user("testuser", "pass")
    fetched = await UserService.get_user_by_username("testuser")
    assert fetched is not None
    assert fetched.username == "testuser"
    
    missing = await UserService.get_user_by_username("nonexistent")
    assert missing is None

@pytest.mark.asyncio
async def test_create_user():
    user = await UserService.create_user("newuser", "secure", is_superuser=True)
    assert user.username == "newuser"
    assert user.is_superuser is True
    # Verify hash
    assert bcrypt.checkpw(b"secure", user.password_hash.encode("utf-8"))

@pytest.mark.asyncio
async def test_verify_password():
    password_hash = bcrypt.hashpw(b"mypass", bcrypt.gensalt()).decode("utf-8")
    assert await UserService.verify_password("mypass", password_hash) is True
    assert await UserService.verify_password("wrongpass", password_hash) is False

@pytest.mark.asyncio
async def test_verify_superuser():
    await UserService.create_user("super", "superpass", is_superuser=True)
    await UserService.create_user("normal", "normalpass", is_superuser=False)
    
    assert await UserService.verify_superuser("super", "superpass") is True
    assert await UserService.verify_superuser("super", "wrong") is False
    assert await UserService.verify_superuser("normal", "normalpass") is False
    assert await UserService.verify_superuser("unknown", "pass") is False

@pytest.mark.asyncio
async def test_update_password():
    user = await UserService.create_user("updateme", "oldpass")
    await UserService.update_password(user, "newpass")
    
    fetched = await UserService.get_user_by_username("updateme")
    assert await UserService.verify_password("newpass", fetched.password_hash) is True
    assert await UserService.verify_password("oldpass", fetched.password_hash) is False
