from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from src.services import HistoryService, LLMService, SettingsService, UserService
from src.database.models import AllowedChat, Setting

BASE_DIR = Path(__file__).resolve().parent

router = APIRouter(prefix="/admin", tags=["admin"])

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


async def get_current_user(request: Request) -> str:
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return user


async def verify_session(request: Request):
    user = request.cookies.get("admin_user")
    if not user:
        raise HTTPException(status_code=status.HTTP_307_TEMPORARY_REDIRECT, headers={"Location": "/admin/login"})
    return user


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "no_header": True})


@router.post("/login", response_class=HTMLResponse)
async def login_post(
    request: Request, 
    username: str = Form(...), 
    password: str = Form(...)
):
    if await UserService.verify_superuser(username, password):
        response = RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(key="admin_user", value=username, httponly=True)
        return response
    
    return templates.TemplateResponse(
        "login.html", 
        {"request": request, "error": "Неверные учетные данные", "no_header": True},
        status_code=400
    )


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("admin_user")
    return response


@router.get("", response_class=HTMLResponse)
async def admin_page(
    request: Request, 
    user: str = Depends(verify_session)
):
    stats = await HistoryService.get_stats()
    chats = await HistoryService.list_chats()
    System_prompt = await SettingsService.get_system_prompt()
    connections = await LLMService.list_connections()
    
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "stats": stats,
            "chats": chats,
            "prompt": System_prompt,
            "connections": connections
        }
    )

# --- API Endpoints (Protected by session) ---

async def verify_api_session(request: Request):
    user = request.cookies.get("admin_user")
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user

@router.get("/api/stats")
async def api_stats(_: Annotated[str, Depends(verify_api_session)]) -> dict:
    return await HistoryService.get_stats()


@router.get("/api/chats")
async def api_chats(_: Annotated[str, Depends(verify_api_session)]) -> list:
    return await HistoryService.list_chats()


@router.post("/api/clear-all")
async def api_clear_all(_: Annotated[str, Depends(verify_api_session)]) -> dict:
    await HistoryService.clear_all_history()
    return {"ok": True}


@router.post("/api/clear/{chat_id:int}")
async def api_clear_chat(chat_id: int, _: Annotated[str, Depends(verify_api_session)]) -> dict:
    await HistoryService.clear_history(chat_id)
    return {"ok": True}


@router.get("/api/prompt")
async def api_get_prompt(_: Annotated[str, Depends(verify_api_session)]) -> dict:
    return {"content": await SettingsService.get_system_prompt()}


@router.get("/api/llm/connections")
async def api_list_connections(_: Annotated[str, Depends(verify_api_session)]) -> list:
    connections = await LLMService.list_connections()
    return [
        {
            "id": c.id,
            "name": c.name,
            "provider": c.provider,
            "model_name": c.model_name,
            "is_active": c.is_active,
        }
        for c in connections
    ]


@router.post("/api/llm/connections")
async def api_create_connection(request: Request, _: Annotated[str, Depends(verify_api_session)]) -> dict:
    data = await request.json()
    conn = await LLMService.create_connection(
        name=data["name"],
        provider=data.get("provider", "openrouter"),
        api_key=data["api_key"],
        model_name=data["model_name"],
        base_url=data.get("base_url"),
        is_active=data.get("is_active", False),
    )
    return {"id": conn.id}


@router.get("/api/llm/connections/{conn_id}")
async def api_get_connection(conn_id: int, _: Annotated[str, Depends(verify_api_session)]) -> dict:
    conn = await LLMService.get_connection(conn_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    return {
        "id": conn.id,
        "name": conn.name,
        "provider": conn.provider,
        "model_name": conn.model_name,
        "api_key": conn.api_key,
        "base_url": conn.base_url,
    }


@router.put("/api/llm/connections/{conn_id}")
async def api_update_connection(conn_id: int, request: Request, _: Annotated[str, Depends(verify_api_session)]) -> dict:
    data = await request.json()
    conn = await LLMService.update_connection(
        connection_id=conn_id,
        name=data["name"],
        provider=data.get("provider", "openrouter"),
        api_key=data["api_key"],
        model_name=data["model_name"],
        base_url=data.get("base_url"),
    )
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    return {"id": conn.id}


@router.delete("/api/llm/connections/{conn_id}")
async def api_delete_connection(conn_id: int, _: Annotated[str, Depends(verify_api_session)]) -> dict:
    success = await LLMService.delete_connection(conn_id)
    if not success:
        raise HTTPException(status_code=404, detail="Connection not found")
    return {"ok": True}


@router.post("/api/llm/connections/{conn_id}/activate")
async def api_activate_connection(conn_id: int, _: Annotated[str, Depends(verify_api_session)]) -> dict:
    await LLMService.set_active_connection(conn_id)
    return {"ok": True}


@router.post("/api/llm/connections/{conn_id}/check")
async def api_check_connection(conn_id: int, _: Annotated[str, Depends(verify_api_session)]) -> dict:
    success = await LLMService.check_connection(conn_id)
    return {"ok": success}


@router.post("/api/llm/connections/check-temporary")
async def api_check_temporary_connection(request: Request, _: Annotated[str, Depends(verify_api_session)]) -> dict:
    data = await request.json()
    success = await LLMService.check_temporary_connection(
        provider=data.get("provider", ""),
        api_key=data.get("api_key", ""),
        base_url=data.get("base_url")
    )
    return {"ok": success}


@router.get("/api/llm/connections/{conn_id}/prompts")
async def api_list_prompts(conn_id: int, _: Annotated[str, Depends(verify_api_session)]) -> list:
    prompts = await LLMService.list_prompts(conn_id)
    return [
        {"id": p.id, "name": p.name, "content": p.content, "is_active": p.is_active}
        for p in prompts
    ]


@router.post("/api/llm/connections/{conn_id}/prompts")
async def api_create_prompt(conn_id: int, request: Request, _: Annotated[str, Depends(verify_api_session)]) -> dict:
    data = await request.json()
    prompt = await LLMService.create_prompt(
        connection_id=conn_id,
        name=data["name"],
        content=data["content"],
        is_active=data.get("is_active", False),
    )
    return {"id": prompt.id}


@router.put("/api/llm/prompts/{prompt_id}")
async def api_update_prompt(prompt_id: int, request: Request, _: Annotated[str, Depends(verify_api_session)]) -> dict:
    data = await request.json()
    prompt = await LLMService.update_prompt(
        prompt_id=prompt_id,
        name=data["name"],
        content=data["content"]
    )
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return {"id": prompt.id}


@router.post("/api/llm/prompts/{prompt_id}/activate")
async def api_activate_prompt(prompt_id: int, _: Annotated[str, Depends(verify_api_session)]) -> dict:
    await LLMService.set_active_prompt(prompt_id)
    return {"ok": True}


@router.delete("/api/llm/prompts/{prompt_id}")
async def api_delete_prompt(prompt_id: int, _: Annotated[str, Depends(verify_api_session)]) -> dict:
    success = await LLMService.delete_prompt(prompt_id)
    if not success:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return {"ok": True}


# --- Whitelist & Settings API ---

@router.get("/api/whitelist")
async def api_get_whitelist(_: Annotated[str, Depends(verify_api_session)]) -> list:
    chats = await AllowedChat.all().order_by("-created_at")
    return [
        {
            "id": c.id,
            "chat_id": str(c.chat_id),
            "title": c.title,
            "is_active": c.is_active,
            "created_at": c.created_at.isoformat()
        }
        for c in chats
    ]


@router.post("/api/whitelist")
async def api_add_whitelist(request: Request, _: Annotated[str, Depends(verify_api_session)]) -> dict:
    data = await request.json()
    chat_id = int(data["chat_id"])
    title = data.get("title", f"Group {chat_id}")
    
    # Check if exists
    exists = await AllowedChat.filter(chat_id=chat_id).exists()
    if exists:
         raise HTTPException(status_code=400, detail="Chat ID already in whitelist")

    chat = await AllowedChat.create(chat_id=chat_id, title=title, is_active=True)
    return {"id": chat.id}


@router.delete("/api/whitelist/{item_id}")
async def api_delete_whitelist(item_id: int, _: Annotated[str, Depends(verify_api_session)]) -> dict:
    deleted_count = await AllowedChat.filter(id=item_id).delete()
    if not deleted_count:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"ok": True}


@router.post("/api/whitelist/{item_id}/toggle")
async def api_toggle_whitelist(item_id: int, request: Request, _: Annotated[str, Depends(verify_api_session)]) -> dict:
    data = await request.json()
    is_active = bool(data.get("is_active", True))
    
    updated_count = await AllowedChat.filter(id=item_id).update(is_active=is_active)
    if not updated_count:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"ok": True}


@router.get("/api/settings/private-chat")
async def api_get_private_chat_setting(_: Annotated[str, Depends(verify_api_session)]) -> dict:
    setting = await Setting.get_or_none(key="allow_private_chat")
    value = str(setting.value).lower() == "true" if setting else True # Default True
    return {"enabled": value}


@router.post("/api/settings/private-chat")
async def api_set_private_chat_setting(request: Request, _: Annotated[str, Depends(verify_api_session)]) -> dict:
    data = await request.json()
    enabled = bool(data.get("enabled", True))
    
    await Setting.update_or_create(
        key="allow_private_chat",
        defaults={"value": str(enabled)}
    )
    return {"ok": True}
