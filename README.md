<p align="center">
  <img src="src/web/static/images/llm_bot_admin_logo.png" alt="LLM Bot Admin Logo" width="200">
</p>

# 🤖 AI Multi-Platform Bot & Admin Panel

![Python](https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.128.0-009688?style=for-the-badge&logo=fastapi)
![Aiogram](https://img.shields.io/badge/Aiogram-3.15.0-blue?style=for-the-badge&logo=telegram)
![Discord.py](https://img.shields.io/badge/Discord.py-2.3.2-blue?style=for-the-badge&logo=discord)
![Docker](https://img.shields.io/badge/Docker-20.10+-2496ED?style=for-the-badge&logo=docker)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

Это мощный мультиплатформенный бот (Telegram & Discord) с интеграцией LLM (OpenRouter, OpenAI, Groq и др.), оснащенный профессиональной панелью управления. Полностью контейнеризирован и готов к развертыванию.

---

## ✨ Основные возможности

### 🤖 Боты (Telegram & Discord)

- **Мультиплатформенность**: Одновременная работа в Telegram и Discord с общими настройками LLM.
- **Контекстное общение**: Боты помнят историю диалога (размер настраивается индивидуально для каждой платформы).
- **Поддержка множества моделей**: Переключение между моделями через админку без перезапуска.
- **Управление историей**: Команда `/clear` в Telegram для очистки истории текущего чата.
- **Интеллектуальная фильтрация**: Ответы только при упоминании (mention) в группах или в разрешенных каналах.
- **Никнеймы**: Сохранение имен пользователей в истории для более точных ответов LLM.
- **Музыкальный плеер (Discord)**: Полнофункциональный проигрыватель с поиском YouTube (до 100 результатов), поддержкой плейлистов, пагинацией очереди и поиска, интерактивным UI, автоматической очисткой и логикой перезапуска.
- **Справка**: Команда `/help` в Discord для быстрого доступа к списку всех команд.

### 🛠 Панель управления (Admin Panel)

- **Премиальный интерфейс**: Современный адаптивный дизайн в стиле Neo-Glass с поддержкой Темной и Светлой темы.
- **Кастомная типографика**: Использование шрифта `IBM Plex Mono` для идеального консольного вида и читаемости.
- **Интерактивные курсоры**: Кастомная векторная стрелка и контекстные курсоры, обеспечивающие единый стиль взаимодействия.
- **Визуальный отклик**: Анимированные эффекты пульсации и «разлетающихся пикселей» при нажатии (Retro Game Click Effect).
- **Централизованные настройки**: Управление доступом, лимитами памяти и активностью ботов для обеих платформ.
- **Управление подключениями**: Добавление, редактирование и проверка LLM-провайдеров через UI.
- **Библиотека промптов**: Создание и активация системных промптов с привязкой к подключениям.
- **Расширенная статистика**: Мониторинг активности по платформам, ролям и времени (за последние 24 часа).
- **Белый список (Whitelist)**: Управление разрешенными группами, супергруппами (Telegram) и серверами/каналами (Discord).
- **Управление музыкальным плеером**: Включение/выключение музыкального функционала Discord бота через админ-панель.
- **Безопасность**: Защищенный вход (Cookie-based Session).

---

## 🛠 Технологический стек

- **Core**: [Python 3.11+](https://www.python.org/)
- **Web Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **SDKs**: [Aiogram 3.x](https://docs.aiogram.dev/) & [Discord.py](https://discordpy.readthedocs.io/)
- **Database / ORM**: [Tortoise ORM](https://tortoise.github.io/) + [Aerich](https://github.com/tortoise/aerich) (Миграции)
- **Database Engine**: [PostgreSQL](https://www.postgresql.org/)
- **Infrastructure**: [Docker](https://www.docker.com/) & [Docker Compose](https://docs.docker.com/compose/)
- **Reverse Proxy**: [Nginx](https://www.nginx.com/)

---

## 🚀 Быстрый старт (Docker)

### 1. Подготовка окружения

Клонируйте репозиторий и создайте файл конфигурации:

```bash
cp .env.example .env
```

### 2. Настройка `.env`

Обязательно заполните следующие поля:

- `BOT_TOKEN`: Токен Telegram бота.
- `DISCORD_BOT_TOKEN`: Токен Discord бота.
- `BASE_WEBHOOK_URL`: Публичный URL вашего сервера.
- `ADMIN_USERNAME` & `ADMIN_PASSWORD`: Учетные данные для админки.

### 3. Запуск

```bash
docker compose up -d --build
```

**После запуска:**

- Боты начнут работу (Telegram через webhook/polling, Discord в фоне).
- Админ-панель: `http://localhost/admin`.
- Логи: `./logs`.

---

## 🧪 Screenshots

<details>
  <summary>Посмотреть скриншоты</summary>

### Вход в систему

  <img src="screenshots/login.jpg" width="750" alt="Login">

### Дашборд и Статистика

  <img src="screenshots/admin-panel.jpg" width="750" alt="Dashboard">

### Настройки доступа и Белый список

  <img src="screenshots/settings.jpg" width="750" alt="Settings">

### Чаты

  <img src="screenshots/chats.jpg" width="750" alt="Chats">

### Статистика

  <img src="screenshots/statistic.jpg" width="750" alt="statistic">

</details>

---

## ⚙️ Конфигурация (.env)

| Переменная | Описание |
|------------|----------|
| `BOT_TOKEN` | Токен Telegram бота |
| `DISCORD_BOT_TOKEN` | Токен Discord бота |
| `BASE_WEBHOOK_URL` | Публичный HTTPS адрес (для Telegram Webhook) |
| `ADMIN_USERNAME` | Логин администратора |
| `ADMIN_PASSWORD` | Пароль администратора |
| `TELEGRAM_ADMIN_IDS` | ID Telegram пользователей для управления промптами |
| `HISTORY_SIZE` | Размер истории по умолчанию |

---

## 📝 Разработка и обслуживание

- **Логи**: `docker compose logs -f bot`
- **Миграции**: Автоматически применяются при запуске через `aerich`.
- **Сброс данных**: `docker compose down -v`

---

## 📚 Документация

Подробная документация доступна в папке `docs/`:

- **[DEPLOYMENT.md](docs/DEPLOYMENT.md)** — Полное руководство по развертыванию проекта
- **[TELEGRAM_BOT.md](docs/TELEGRAM_BOT.md)** — Документация по Telegram боту
- **[DISCORD_BOT.md](docs/DISCORD_BOT.md)** — Документация по Discord боту и музыкальному плееру

---

## 📄 Лицензия

Этот проект распространяется под лицензией MIT.

---
*Developed with ❤️ as a professional Multi-Platform LLM Solution.*
