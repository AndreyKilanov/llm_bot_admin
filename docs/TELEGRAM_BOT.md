# Telegram Бот - Документация

## 📋 Содержание

- [Обзор](#обзор)
- [Архитектура](#архитектура)
- [Команды бота](#команды-бота)
- [Настройки](#настройки)
- [Система Whitelist](#система-whitelist)
- [Логика работы в группах](#логика-работы-в-группах)
- [Интеграция с LLM](#интеграция-с-llm)
- [Примеры использования](#примеры-использования)

## Обзор

Telegram бот предоставляет интерфейс для взаимодействия с большой языковой моделью (LLM) через мессенджер Telegram. Бот поддерживает как личные сообщения, так и работу в группах.

### Основные возможности

- ✅ Интеграция с LLM для генерации ответов
- ✅ Поддержка личных сообщений и групповых чатов
- ✅ Система whitelist для контроля доступа
- ✅ Управление историей диалогов
- ✅ Настройка системного промпта
- ✅ Логирование всех взаимодействий
- ✅ Административные команды для управления

## Архитектура

### Структура пакета

```text
src/bot/telegram/
├── __init__.py          # Экспорт компонентов
├── handlers.py          # Обработчики команд и сообщений
└── middleware.py        # Middleware для фильтрации
```

### Компоненты

#### 1. Handlers (handlers.py)

Модуль содержит все обработчики команд и сообщений.

**Основные функции:**

- `cmd_start()` - Приветственное сообщение при первом запуске
- `cmd_help()` - Справка по доступным командам
- `cmd_clear()` - Очистка истории диалога
- `cmd_prompt()` - Просмотр текущего системного промпта
- `cmd_set_prompt()` - Установка нового системного промпта (только для администраторов)
- `cmd_cancel()` - Отмена текущей операции
- `on_text()` - Обработка всех текстовых сообщений

#### 2. Middleware (middleware.py)

Модуль содержит middleware для обработки входящих сообщений.

**Классы:**

**LoggingMiddleware** - Логирование всех входящих сообщений

- Записывает информацию о пользователе
- Записывает текст сообщения
- Записывает тип чата

**WhitelistMiddleware** - Проверка доступа к боту

- Проверяет активность бота (`telegram_bot_enabled`)
- Проверяет наличие чата в whitelist
- Проверяет глобальные настройки (`telegram_allow_new_chats`)
- Проверяет разрешение личных сообщений (`allow_private_chat`)

## Команды бота

### Пользовательские команды

| Команда   | Описание                            | Пример    |
|-----------|-------------------------------------|-----------|
| `/start`  | Начать работу с ботом               | `/start`  |
| `/help`   | Показать справку по командам        | `/help`   |
| `/clear`  | Очистить историю диалога            | `/clear`  |
| `/prompt` | Посмотреть текущий системный промпт | `/prompt` |

### Административные команды

| Команда       | Описание                          | Пример        |
|---------------|-----------------------------------|---------------|
| `/set_prompt` | Установить новый системный промпт | `/set_prompt` |
| `/cancel`     | Отменить текущую операцию         | `/cancel`     |

**Примечание:** Административные команды доступны только пользователям, указанным в переменной окружения `TELEGRAM_ADMIN_IDS`.

## Настройки

Настройки бота хранятся в базе данных (таблица `settings`) и управляются через админ-панель.

### Доступные настройки

| Ключ                       | Тип     | Описание                   | По умолчанию |
|----------------------------|---------|----------------------------|--------------|
| `ENABLE_TELEGRAM`     | boolean | Включение инициализации бота при старте | `true` (env) |
| `telegram_bot_enabled`     | boolean | Включение/выключение бота в БД  | `true`       |
| `telegram_allow_new_chats` | boolean | Разрешить новые чаты       | `true`       |
| `allow_private_chat`       | boolean | Разрешить личные сообщения | `true`       |
| `telegram_memory_limit`    | integer | Лимит истории сообщений    | `10`         |
| `system_prompt`            | string  | Системный промпт для LLM   | -            |

### Как изменить настройки

1. **Через админ-панель:**
   - Откройте `http://localhost/admin`
   - Перейдите в раздел "Настройки"
   - Измените нужные параметры
   - Нажмите "Сохранить"

2. **Через команду (только системный промпт):**

   ```text
   /set_prompt
   <введите новый промпт>
   ```

## Система Whitelist

Бот использует систему whitelist для контроля доступа к функционалу.

### Как работает Whitelist

1. **Проверка активности бота** - Проверяется настройка `telegram_bot_enabled`
   - Если `false` - бот не отвечает никому

2. **Проверка whitelist** - Проверяется наличие чата в таблице `allowed_chats`
   - Если чат есть и `is_active=true` - доступ разрешён
   - Если чат есть и `is_active=false` - доступ запрещён

3. **Проверка глобальных настроек** - Если чата нет в whitelist:
   - Для групп: проверяется `telegram_allow_new_chats`
   - Для личных сообщений: проверяется `allow_private_chat`

### Управление Whitelist

**Через админ-панель:**

1. Откройте `http://localhost/admin`
2. Перейдите в раздел "Whitelist"
3. Добавьте/удалите/активируйте/деактивируйте чаты

**Автоматическое добавление:**

- Новые чаты автоматически добавляются в whitelist при первом сообщении (если разрешено настройками)

## Логика работы в группах

В групповых чатах бот отвечает только при определённых условиях:

### Условия ответа в группах

1. **Упоминание бота** - Сообщение содержит `@bot_username`

   ```text
   @mybot привет!
   ```

2. **Ответ на сообщение бота** - Сообщение является реплаем на сообщение бота

   ```text
   [Сообщение бота]
     └─ [Ответ пользователя]  ← Бот ответит
   ```

### Логика работы в личных сообщениях

В личных сообщениях бот отвечает на все текстовые сообщения (если разрешено настройками).

## Интеграция с LLM

Бот использует `LLMService` для генерации ответов на основе истории диалога.

### Поток обработки сообщения

```text
1. Пользователь отправляет сообщение
   ↓
2. LoggingMiddleware логирует сообщение
   ↓
3. WhitelistMiddleware проверяет доступ
   ↓
4. Сообщение сохраняется в историю (HistoryService)
   ↓
5. Получается история последних N сообщений
   ↓
6. История отправляется в LLMService
   ↓
7. LLM генерирует ответ
   ↓
8. Ответ сохраняется в историю
   ↓
9. Ответ отправляется пользователю
```

### Формат истории

```python
[
    {"role": "system", "content": "Ты полезный ассистент..."},
    {"role": "user", "content": "Привет!"},
    {"role": "assistant", "content": "Здравствуйте!"},
    {"role": "user", "content": "Как дела?"},
]
```

### Обработка ошибок

При ошибках генерации ответа:

1. Ошибка логируется с полным stack trace
2. Пользователю отправляется сообщение: "Произошла ошибка при генерации ответа"
3. История не сохраняется (откат транзакции)

## Примеры использования

### Инициализация бота

```python
from aiogram import Bot, Dispatcher
from src.bot.telegram import router, LoggingMiddleware, WhitelistMiddleware

# Создание бота и диспетчера
bot = Bot(token="YOUR_TELEGRAM_TOKEN")
dp = Dispatcher()

# Подключение роутера
dp.include_router(router)

# Подключение middleware
dp.message.middleware(LoggingMiddleware())
dp.message.outer_middleware(WhitelistMiddleware())

# Запуск
await dp.start_polling(bot)
```

### Настройка администраторов

Администраторы указываются в переменной окружения:

```env
TELEGRAM_ADMIN_IDS=123456789,987654321
```

### Добавление нового обработчика команды

```python
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()

@router.message(Command("mycommand"))
async def cmd_mycommand(message: Message) -> None:
    """Обработчик пользовательской команды."""
    await message.answer("Ответ на команду")
```

### Добавление нового middleware

```python
from aiogram import BaseMiddleware
from aiogram.types import Message
from typing import Callable, Dict, Any, Awaitable

class MyMiddleware(BaseMiddleware):
    """Пользовательский middleware."""
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        # Логика до обработчика
        print(f"Получено сообщение: {event.text}")
        
        # Вызов обработчика
        result = await handler(event, data)
        
        # Логика после обработчика
        print("Сообщение обработано")
        
        return result
```

### Работа с историей сообщений

```python
from src.services import HistoryService

# Добавление сообщения в историю
await HistoryService.add_message(
    chat_id=message.chat.id,
    role="user",
    content=message.text,
    platform="telegram",
    chat_title=message.chat.title,
    nickname=message.from_user.username
)

# Получение истории
history = await HistoryService.get_last_messages(
    chat_id=message.chat.id,
    limit=10,
    platform="telegram"
)

# Очистка истории
await HistoryService.clear_history(
    chat_id=message.chat.id,
    platform="telegram"
)
```

### Работа с настройками

```python
from src.services import SettingsService

# Получение системного промпта
system_prompt = await SettingsService.get_system_prompt()

# Установка системного промпта
await SettingsService.set_system_prompt("Новый системный промпт")

# Получение любой настройки
bot_enabled = await SettingsService.get_setting("telegram_bot_enabled", True)
```

## Логирование

Бот использует стандартный модуль `logging` с разными логгерами:

```python
import logging

# Основной логгер Telegram бота
logger = logging.getLogger("bot.telegram")

# Логгер обработчиков
handlers_logger = logging.getLogger("bot.telegram.handlers")

# Логгер middleware
middleware_logger = logging.getLogger("bot.telegram.middleware")
```

### Примеры логирования

```python
logger.info(f"Получено сообщение от пользователя {user_id}")
logger.warning(f"Чат {chat_id} не в whitelist")
logger.error(f"Ошибка при генерации ответа: {error}", exc_info=True)
```

## Тестирование

### Запуск тестов

```bash
# Все тесты Telegram бота
pytest tests/bot/telegram/ -v

# Конкретный тест
pytest tests/bot/telegram/test_whitelist_middleware.py::test_whitelist_allows_active_chat -v
```

### Пример теста

```python
import pytest
from src.bot.telegram.middleware import WhitelistMiddleware

@pytest.mark.asyncio
async def test_whitelist_allows_active_chat():
    """Тест проверки доступа для активного чата."""
    # Arrange
    middleware = WhitelistMiddleware()
    
    # Act
    result = await middleware.check_access(chat_id=123, platform="telegram")
    
    # Assert
    assert result is True
```

## Зависимости

- **aiogram** - Фреймворк для работы с Telegram Bot API
- **tortoise-orm** - ORM для работы с базой данных
- **src.services** - Общие сервисы (LLM, History, Settings)

## См. также

- [Документация Discord бота](DISCORD_BOT.md)
- [Развёртывание проекта](DEPLOYMENT.md)
