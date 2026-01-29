from aiogram import Router
from aiogram.enums import ChatAction, ChatType
from aiogram.filters import Command
from aiogram.types import Message

from src.logger import log_function

from config import Settings
from src.llm.openrouter import get_completion
from src.services import HistoryService, LLMService, SettingsService

router = Router()

_waiting_prompt: set[int] = set()
_bot_username: str | None = None


def _get_admin_ids() -> set[int]:
    s = Settings()
    if not s.TELEGRAM_ADMIN_IDS:
        return set()
    return {int(x.strip()) for x in s.TELEGRAM_ADMIN_IDS.split(",") if x.strip()}


@router.message(Command("start"))
@log_function
async def cmd_start(message: Message) -> None:
    await message.answer(
        "Привет! Я бот с поддержкой LLM. Напиши текст — и я отвечу.\n"
        "Используй /help для списка команд."
    )


@router.message(Command("clear"))
async def cmd_clear(message: Message) -> None:
    await HistoryService.clear_history(message.chat.id)
    await message.answer("История очищена.")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    help_text = """
🤖 **LLM Бот-ассистент**

Я умный бот с поддержкой больших языковых моделей. Могу отвечать на вопросы, помогать с задачами и поддерживать беседу.

**Доступные команды:**
/start - Начать работу с ботом
/help - Показать это сообщение
/clear - Очистить историю диалога
/prompt - Посмотреть текущий системный промпт

**Как использовать:**
Просто напишите мне любой вопрос или задачу, и я постараюсь помочь!
"""
    await message.answer(help_text)


@router.message(Command("prompt"))
async def cmd_prompt(message: Message) -> None:
    text = await SettingsService.get_system_prompt()
    if len(text) > 400:
        text = text[:400] + "\n… (обрезано)"
    await message.answer(f"Текущий промпт:\n\n{text or '(пусто)'}\n\nИзменить: /set_prompt")


@router.message(Command("set_prompt"))
async def cmd_set_prompt(message: Message) -> None:
    admin_ids = _get_admin_ids()
    if not admin_ids or (message.from_user and message.from_user.id not in admin_ids):
        await message.answer("Нет доступа.")
        return
    uid = message.from_user.id if message.from_user else 0
    _waiting_prompt.add(uid)
    await message.answer(
        "Отправьте новый промпт следующим сообщением. /cancel — отмена."
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message) -> None:
    uid = message.from_user.id if message.from_user else 0
    if uid in _waiting_prompt:
        _waiting_prompt.discard(uid)
        await message.answer("Отменено.")


async def _ensure_bot_username(bot) -> str:
    global _bot_username
    if _bot_username is None:
        bot_info = await bot.get_me()
        _bot_username = bot_info.username
    return _bot_username


@router.message()
@log_function
async def on_text(message: Message) -> None:
    if not message.text or not message.text.strip():
        return

    uid = message.from_user.id if message.from_user else 0
    if uid in _waiting_prompt:
        _waiting_prompt.discard(uid)
        await SettingsService.set_system_prompt(message.text.strip())
        await message.answer("Промпт обновлён.")
        return

    # === ФИЛЬТРАЦИЯ ДЛЯ ГРУПП ===
    if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        bot_username = await _ensure_bot_username(message.bot)
        bot_user_id = (await message.bot.get_me()).id

        mentioned = False
        replied_to_bot = False

        # Проверка реплая
        if message.reply_to_message and message.reply_to_message.from_user:
            replied_to_bot = message.reply_to_message.from_user.id == bot_user_id

        # Проверка упоминания
        mention_str = f"@{bot_username}"
        if mention_str.lower() in message.text.lower():
            mentioned = True
            user_text = message.text.lower().replace(mention_str.lower(), "", 1).strip()
        else:
            user_text = message.text.strip()

        if not mentioned and not replied_to_bot:
            return

        if not user_text:
            return
    else:
        user_text = message.text.strip()

    # === ОБРАБОТКА ЗАПРОСА К LLM ===
    chat_id = message.chat.id
    await HistoryService.add_message(chat_id, "user", user_text)
    settings = Settings()
    active_conn = await LLMService.get_active_connection()

    if active_conn:
        api_key = active_conn.api_key
        model = active_conn.model_name
        base_url = active_conn.base_url
        db_prompt = await LLMService.get_active_prompt(active_conn.id)
        system_prompt = db_prompt.content if db_prompt else await SettingsService.get_system_prompt()
    else:
        api_key = settings.OPENROUTER_API_KEY
        model = settings.OPENROUTER_MODEL
        base_url = None
        system_prompt = await SettingsService.get_system_prompt()

    last_messages = await HistoryService.get_last_messages(chat_id, limit=settings.HISTORY_SIZE)
    messages = [{"role": "system", "content": system_prompt}] + last_messages

    await message.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    try:
        reply = await get_completion(
            messages,
            api_key=api_key,
            model=model,
            base_url=base_url
        )
    except Exception as e:
        await message.answer(f"Ошибка при запросе к модели: {e}")
        return

    await HistoryService.add_message(chat_id, "assistant", reply)
    await message.answer(reply)