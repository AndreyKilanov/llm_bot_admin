import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI
from unittest.mock import AsyncMock, patch

from src.web.admin import router, verify_session, verify_api_session
from src.database.models import User, AllowedChat, Setting, LLMConnection, LLMPrompt
from src.services.user_service import UserService

@pytest.fixture
def test_app():
    app = FastAPI()
    app.include_router(router)
    
    # Override dependencies to bypass auth for most tests
    app.dependency_overrides[verify_session] = lambda: "admin_user"
    app.dependency_overrides[verify_api_session] = lambda: "admin_user"
    
    return app


@pytest.fixture(autouse=True)
async def clear_db():
    await User.all().delete()
    await AllowedChat.all().delete()
    await Setting.all().delete()
    await LLMConnection.all().delete()
    await LLMPrompt.all().delete()
    yield
    

@pytest.mark.asyncio
async def test_login_page(test_app):
    # Removing override for login testing
    test_app.dependency_overrides = {}
    
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.get("/admin/login")
        assert response.status_code == 200
        assert "login" in response.text.lower()


@pytest.mark.asyncio
async def test_login_post_success(test_app):
    test_app.dependency_overrides = {}
    await UserService.create_user("admin", "password", is_superuser=True)
    
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.post(
            "/admin/login", 
            data={"username": "admin", "password": "password"},
            follow_redirects=False
        )
        assert response.status_code == 303
        assert "admin_user" in response.cookies


@pytest.mark.asyncio
async def test_login_post_failure(test_app):
    test_app.dependency_overrides = {}
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.post(
            "/admin/login", 
            data={"username": "admin", "password": "wrong"},
            follow_redirects=False
        )
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_logout(test_app):
    test_app.dependency_overrides = {}
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test", cookies={"admin_user": "admin"}) as client:
        response = await client.get("/admin/logout", follow_redirects=False)
        assert response.status_code == 303
        # Cookie should be deleted or expired
        assert not response.cookies.get("admin_user") or response.cookies.get("admin_user") == '""'


@pytest.mark.asyncio
async def test_admin_page(test_app):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.get("/admin")
        assert response.status_code == 200
        assert "llm bot admin" in response.text.lower()


@pytest.mark.asyncio
async def test_api_stats(test_app):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.get("/admin/api/stats")
        assert response.status_code == 200
        assert "total_messages" in response.json()


@pytest.mark.asyncio
async def test_api_whitelist(test_app):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        # Create whitelist entry
        r1 = await client.post("/admin/api/whitelist", json={"chat_id": 123, "platform": "telegram", "title": "Test Chat"})
        assert r1.status_code == 200
        item_id = r1.json()["id"]

        # Duplicate should fail
        r_dup = await client.post("/admin/api/whitelist", json={"chat_id": 123, "platform": "telegram"})
        assert r_dup.status_code == 400

        # Get whitelist
        r2 = await client.get("/admin/api/whitelist?platform=telegram")
        assert r2.status_code == 200
        assert len(r2.json()) == 1
        assert r2.json()[0]["chat_id"] == "123"

        # Toggle active
        r3 = await client.post(f"/admin/api/whitelist/{item_id}/toggle", json={"is_active": False})
        assert r3.status_code == 200

        # Delete
        r4 = await client.delete(f"/admin/api/whitelist/{item_id}")
        assert r4.status_code == 200


@pytest.mark.asyncio
async def test_api_llm_connections(test_app):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        # Create connection
        r1 = await client.post("/admin/api/llm/connections", json={
            "name": "TestConn", "provider": "openai", "api_key": "key", "model_name": "gpt-4o", "is_active": True
        })
        assert r1.status_code == 200
        conn_id = r1.json()["id"]

        # List connections
        r2 = await client.get("/admin/api/llm/connections")
        assert r2.status_code == 200
        assert len(r2.json()) == 1

        # Get connection
        r3 = await client.get(f"/admin/api/llm/connections/{conn_id}")
        assert r3.status_code == 200
        assert r3.json()["name"] == "TestConn"

        # Update connection
        r4 = await client.put(f"/admin/api/llm/connections/{conn_id}", json={
            "name": "Updated", "provider": "openai", "api_key": "new_key", "model_name": "gpt-4"
        })
        assert r4.status_code == 200

        # Create prompt
        r5 = await client.post(f"/admin/api/llm/connections/{conn_id}/prompts", json={
            "name": "Prompt", "content": "You are helpful", "is_active": True
        })
        assert r5.status_code == 200
        prompt_id = r5.json()["id"]

        # List prompts
        r6 = await client.get(f"/admin/api/llm/connections/{conn_id}/prompts")
        assert r6.status_code == 200
        assert len(r6.json()) == 1

        # Delete operations
        rd1 = await client.delete(f"/admin/api/llm/prompts/{prompt_id}")
        assert rd1.status_code == 200

        rd2 = await client.delete(f"/admin/api/llm/connections/{conn_id}")
        assert rd2.status_code == 200


@pytest.mark.asyncio
async def test_api_global_settings(test_app):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        r1 = await client.post("/admin/api/settings/global", json={
            "telegram": {"enabled": False, "allow_private": False, "allow_new_chats": False, "memory_limit": 5},
            "discord": {"enabled": True, "allow_dms": True, "allow_new_chats": True, "music_enabled": True, "memory_limit": 10, "seek_time": 20}
        })
        assert r1.status_code == 200

        r2 = await client.get("/admin/api/settings/global")
        assert r2.status_code == 200
        data = r2.json()
        assert data["telegram"]["enabled"] is False
        assert data["discord"]["enabled"] is True
        assert data["telegram"]["memory_limit"] == 5
        assert data["discord"]["seek_time"] == 20
