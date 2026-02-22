import pytest
from tortoise import Tortoise
from src.database.models import AllowedChat, Setting, User
from src.services import UserService
from src.web.app import create_app
from httpx import AsyncClient, ASGITransport
from unittest.mock import MagicMock


@pytest.fixture
async def client():
    # Create a mock bot and dispatcher since we don't need them for admin API tests
    bot = MagicMock()
    bot.get_me = MagicMock()
    dp = MagicMock()
    
    app = create_app(bot, dp)
    
    # Bypass cookie verification by mocking dependency or just setting cookie
    # But since verifies_session checks cookie, we need to handle that.
    # In integration tests, it's easier to use a valid session cookie.
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        # Create admin user
        await UserService.create_user("admin", "admin", is_superuser=True)
        # Login to get cookie
        response = await c.post("/admin/login", data={"username": "admin", "password": "admin"})
        assert response.status_code == 303
        
        yield c

@pytest.mark.asyncio
async def test_whitelist_api(client):
    # Add whitelist item
    resp = await client.post("/admin/api/whitelist", json={"chat_id": 12345, "title": "Test Group"})
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    item_id = data["id"]
    
    # Get whitelist
    resp = await client.get("/admin/api/whitelist")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["chat_id"] == "12345"
    assert items[0]["title"] == "Test Group"
    
    # Duplicate check
    resp = await client.post("/admin/api/whitelist", json={"chat_id": 12345, "title": "Duplicate"})
    assert resp.status_code == 400
    
    # Delete
    resp = await client.delete(f"/admin/api/whitelist/{item_id}")
    assert resp.status_code == 200
    
    # Verify empty
    resp = await client.get("/admin/api/whitelist")
    assert len(resp.json()) == 0

@pytest.mark.asyncio
async def test_settings_private_chat_api(client):
    # Default should be true
    resp = await client.get("/admin/api/settings/global")
    assert resp.status_code == 200
    assert resp.json()["telegram"]["allow_private"] is True
    
    # Disable
    payload = {
        "telegram": {
            "allow_private": False
        }
    }
    resp = await client.post("/admin/api/settings/global", json=payload)
    assert resp.status_code == 200
    
    # Verify
    resp = await client.get("/admin/api/settings/global")
    assert resp.json()["telegram"]["allow_private"] is False
    
    # Check DB directly
    setting = await Setting.get(key="allow_private_chat")
    assert setting.value == "False"
