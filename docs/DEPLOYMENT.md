# Развёртывание проекта LLM Bot

## 📋 Содержание

- [Обзор проекта](#обзор-проекта)
- [Требования](#требования)
- [Установка](#установка)
- [Конфигурация](#конфигурация)
- [Запуск через Docker](#запуск-через-docker)
- [Запуск без Docker](#запуск-без-docker)
- [Конфигурация портов](#конфигурация-портов)
- [Развёртывание музыкального функционала](#развёртывание-музыкального-функционала)
- [Мониторинг и логирование](#мониторинг-и-логирование)
- [Решение проблем](#решение-проблем)

## Обзор проекта

LLM Bot - система ботов для взаимодействия с большими языковыми моделями через Telegram и Discord.

### Основные возможности

**Telegram бот:**

- ✅ Интеграция с LLM для генерации ответов
- ✅ Поддержка личных сообщений и групп
- ✅ Система whitelist для контроля доступа
- ✅ Управление историей диалогов
- ✅ Настройка системного промпта

**Discord бот:**

- ✅ Интеграция с LLM для генерации ответов
- ✅ Поддержка личных сообщений и серверов
- ✅ Система whitelist для контроля доступа
- ✅ Музыкальный плеер с воспроизведением из YouTube
- ✅ Интерактивный UI с кнопками управления
- ✅ Очередь треков и прогресс-бар

**Веб-интерфейс:**

- ✅ Админ-панель для управления
- ✅ Просмотр статистики использования
- ✅ Управление whitelist
- ✅ Настройка ботов
- ✅ Просмотр истории сообщений

## Требования

### Системные требования

- **Docker** и **Docker Compose** (для запуска через Docker)
- **Python 3.13+** (для запуска без Docker)
- **PostgreSQL** (или SQLite для разработки)

### Системные библиотеки (для Discord музыки)

- **libopus** - Для голосовой связи Discord
- **libsodium** - Для шифрования голосовой связи
- **ffmpeg** - Для обработки аудио

## Установка

### 1. Клонирование репозитория

```bash
git clone https://github.com/yourusername/llm_bot_admin.git
cd llm_bot_admin
```

### 2. Настройка переменных окружения

```bash
# Создайте файл .env на основе примера
cp .env.example .env
```

Отредактируйте `.env` файл (см. раздел [Конфигурация](#конфигурация))

## Конфигурация

### Переменные окружения (.env)

```env
# Telegram
BOT_TOKEN=your_telegram_bot_token
TELEGRAM_ADMIN_IDS=123456789,987654321

# Discord
DISCORD_BOT_TOKEN=your_discord_bot_token

# База данных
DATABASE_URL=postgresql://user:password@db:5432/llm_bot
# Для разработки можно использовать SQLite:
# DATABASE_URL=sqlite://db.sqlite3

# LLM (OpenAI)
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4

# Веб-сервер
HOST=0.0.0.0
PORT=8000

# Docker порты
APP_PORT=8000      # Внутренний порт приложения
DB_PORT=5432       # Внешний порт PostgreSQL (для подключения с хоста)
NGINX_PORT=80      # Внешний порт Nginx (доступен на хосте)
```

### Настройки в базе данных

Настройки хранятся в таблице `settings` и управляются через админ-панель:

**Общие настройки:**

- `system_prompt` - Системный промпт для LLM

**Telegram:**

- `telegram_bot_enabled` - Включение/выключение бота (по умолчанию: `true`)
- `telegram_allow_new_chats` - Разрешить новые чаты (по умолчанию: `true`)
- `allow_private_chat` - Разрешить личные сообщения (по умолчанию: `true`)
- `telegram_memory_limit` - Лимит истории сообщений (по умолчанию: `10`)

**Discord:**

- `discord_bot_enabled` - Включение/выключение бота (по умолчанию: `true`)
- `discord_allow_new_chats` - Разрешить новые чаты (по умолчанию: `false`)
- `discord_allow_dms` - Разрешить личные сообщения (по умолчанию: `true`)
- `discord_memory_limit` - Лимит истории сообщений (по умолчанию: `10`)

## Запуск через Docker

### Быстрый старт

```bash
# Сборка и запуск всех сервисов
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Просмотр логов конкретного сервиса
docker-compose logs -f app
```

### Остановка

```bash
# Остановка всех сервисов
docker-compose down

# Остановка с удалением volumes
docker-compose down -v
```

### Пересборка образа

```bash
# Пересборка с новыми зависимостями
docker-compose build

# Пересборка без кэша
docker-compose build --no-cache
```

### Структура Docker Compose

Проект использует следующие сервисы:

1. **app** - Основное приложение (боты + веб-интерфейс)
   - Порт: `${APP_PORT}` (внутри контейнера)
   - Не пробрасывается наружу (доступен только через nginx)

2. **db** - PostgreSQL база данных
   - Внутренний порт: `5432`
   - Внешний порт: `${DB_PORT}:5432`
   - Volume: `postgres_data:/var/lib/postgresql/data`

3. **nginx** - Reverse proxy
   - Внутренний порт: `80`
   - Внешний порт: `${NGINX_PORT}:80`
   - Проксирует запросы на `app:${APP_PORT}`

## Запуск без Docker

### 1. Установка зависимостей и окружения

```bash
# Использование uv для установки зависимостей (окружение создастся автоматически)
uv sync
```

### 2. Инициализация базы данных

```bash
uv run python -m src.database.init_db
```

### 3. Запуск приложения

```bash
uv run python -m src.main
```

## Конфигурация портов

### Стандартные порты (по умолчанию)

```env
APP_PORT=8000
DB_PORT=5432
NGINX_PORT=80
```

**Доступ:**

- Веб-интерфейс: `http://localhost:80`
- База данных: `localhost:5432`
- Админ-панель: `http://localhost:80/admin`

### Кастомные порты

Если стандартные порты заняты, измените их в `.env`:

```env
APP_PORT=8000
DB_PORT=5433
NGINX_PORT=8080
```

**Доступ:**

- Веб-интерфейс: `http://localhost:8080`
- База данных: `localhost:5433`
- Админ-панель: `http://localhost:8080/admin`

### Как это работает

- **Nginx** автоматически обрабатывает файлы `.template` из `/etc/nginx/templates/`
- При запуске контейнера nginx подставляет переменные окружения и создает финальную конфигурацию
- Не нужно вручную генерировать конфигурацию nginx

## Развёртывание музыкального функционала

### Требования

- **FFmpeg** - устанавливается автоматически в Docker
- **libopus** - устанавливается автоматически в Docker
- **libsodium** - устанавливается автоматически в Docker
- **Голосовой канал** - пользователь должен быть в голосовом канале Discord
- **Права бота** - бот должен иметь права на подключение к голосовым каналам

### Установка (Docker)

```bash
# Остановить текущие контейнеры
docker-compose down

# Пересобрать образ с новыми зависимостями
docker-compose build

# Запустить контейнеры
docker-compose up -d
```

### Проверка установки

```bash
# Проверить логи запуска
docker-compose logs -f app

# Должны увидеть:
# Discord Bot connected as <имя_бота>

# Проверить наличие FFmpeg
docker-compose exec app ffmpeg -version
```

### Тестирование музыкального функционала

1. Подключитесь к голосовому каналу на вашем Discord сервере
2. Выполните команду: `/playmusic Never Gonna Give You Up`
3. Бот должен подключиться к каналу и начать воспроизведение

### Права бота в Discord

Убедитесь, что бот имеет следующие права:

- **Voice: Connect** - Подключение к голосовым каналам
- **Voice: Speak** - Воспроизведение звука

## Мониторинг и логирование

### Админ-панель

Доступна по адресу: `http://localhost/admin` (или на вашем `NGINX_PORT`)

**Возможности:**

- Просмотр статистики использования
- Управление whitelist
- Просмотр истории сообщений
- Настройка ботов
- Очистка истории

### Логирование

Система использует стандартный модуль `logging` с разными логгерами:

- `bot.telegram.*` - Telegram бот
- `discord.*` - Discord бот
- `services.*` - Сервисы
- `web.*` - Веб-интерфейс

**Просмотр логов Docker:**

```bash
# Все логи
docker-compose logs -f

# Логи приложения
docker-compose logs -f app

# Логи базы данных
docker-compose logs -f db

# Логи nginx
docker-compose logs -f nginx
```

### Мониторинг ресурсов

```bash
# Использование ресурсов контейнерами
docker stats

# Информация о контейнерах
docker-compose ps
```

## Решение проблем

### Бот не подключается к голосовому каналу (Discord)

**Решение:** Проверьте права бота в настройках Discord сервера:

- Voice: Connect
- Voice: Speak

### Ошибка при поиске треков

**Решение:** Проверьте логи на наличие ошибок от yt-dlp:

```bash
docker-compose logs -f app | grep yt-dlp
```

Возможно, YouTube изменил API. Обновите yt-dlp:

```bash
docker-compose exec app pip install --upgrade yt-dlp
```

### Нет звука в Discord

**Решение:**

1. Проверьте, что FFmpeg установлен:

   ```bash
   docker-compose exec app ffmpeg -version
   ```

2. Проверьте логи на ошибки воспроизведения:

   ```bash
   docker-compose logs -f app | grep "music_player"
   ```

3. Убедитесь, что установлены libopus и libsodium

### Ошибки подключения к базе данных

**Решение:**

1. Проверьте, что контейнер базы данных запущен:

   ```bash
   docker-compose ps db
   ```

2. Проверьте переменную `DATABASE_URL` в `.env`

3. Проверьте логи базы данных:

   ```bash
   docker-compose logs -f db
   ```

### Telegram бот не отвечает

**Решение:**

1. Проверьте настройку `telegram_bot_enabled` в админ-панели
2. Проверьте whitelist для чата
3. Проверьте логи:

   ```bash
   docker-compose logs -f app | grep "telegram"
   ```

### Discord бот не отвечает на сообщения

**Решение:**

1. Проверьте настройку `discord_bot_enabled` в админ-панели
2. Убедитесь, что бот упомянут в сообщении (`@BotName`)
3. Проверьте whitelist для сервера/канала
4. Проверьте логи:

   ```bash
   docker-compose logs -f app | grep "discord"
   ```

### Порты заняты

**Решение:** Измените порты в `.env` файле:

```env
NGINX_PORT=8080  # Вместо 80
DB_PORT=5433     # Вместо 5432
```

Затем пересоздайте контейнеры:

```bash
docker-compose down
docker-compose up -d
```

## Тестирование

### Запуск всех тестов

```bash
# В Docker
docker-compose exec app pytest

# Локально
pytest
```

### Запуск тестов для конкретного компонента

```bash
# Telegram
pytest tests/bot/telegram/

# Discord
pytest tests/bot/discord/
```

## Безопасность

- ✅ Whitelist для контроля доступа
- ✅ Административные команды только для админов
- ✅ Валидация всех входных данных
- ✅ Безопасное хранение токенов в переменных окружения
- ✅ Изоляция сервисов через Docker

## Архитектура проекта

```
src/
├── bot/                    # Пакет ботов
│   ├── telegram/          # Telegram бот
│   │   ├── handlers.py    # Обработчики команд
│   │   └── middleware.py  # Middleware
│   └── discord/           # Discord бот
│       ├── bot/           # Основные компоненты бота (клиент, команды)
│       ├── player/        # Аудио-плеер, работа с голосовым каналом и очередью
│       ├── views/         # UI-компоненты (кнопки, пагинация, списки)
│       └── handlers.py    # Обработчик сообщений (LLM-чат)
├── services/              # Общие сервисы
│   ├── llm_service.py    # Интеграция с LLM
│   ├── history_service.py # История сообщений
│   ├── settings_service.py # Настройки
│   └── music_service.py  # Музыка (Discord)
├── database/              # База данных
│   ├── models.py         # Модели данных
│   └── config.py         # Конфигурация БД
└── web/                   # Веб-интерфейс
    ├── app.py            # FastAPI приложение
    └── admin.py          # Админ-панель
tests/                     # Тесты
├── bot/                   # Тесты ботов (discord, telegram)
├── core/                  # Тесты ядра
├── services/              # Тесты сервисов
├── web/                   # Тесты API
├── conftest.py            # Основные настройки pytest
└── fixtures.py            # Переиспользуемые фикстуры
```

## Полезные ссылки

- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Discord.py Documentation](https://discordpy.readthedocs.io/)
- [OpenAI API Documentation](https://platform.openai.com/docs/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [yt-dlp Documentation](https://github.com/yt-dlp/yt-dlp)
