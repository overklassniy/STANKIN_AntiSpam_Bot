# СТАНКИН Анти-спам система

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

Комплексное решение для борьбы со спамом в Telegram-чатах.

## Возможности

- **Telegram-бот** для мониторинга и модерации
- **Веб-панель** для настройки и статистики
- **ML-модели** (RuBERT) для классификации спама
- **Интеграции** с CAS, LOLS, ChatGPT
- **Белый список** пользователей
- **Повторные попытки** отправки уведомлений при ошибках

---

## Быстрый старт

```bash
# 1. Клонируйте репозиторий
git clone https://github.com/overklassniy/STANKIN_AntiSpam_Bot.git
cd STANKIN_AntiSpam_Bot

# 2. Настройте переменные окружения
cp .env.example .env
# Отредактируйте .env и заполните значения

# 3. Запустите через Docker
docker compose up -d

# 4. Инициализируйте БД и создайте администратора
docker compose exec stankin-antispam-bot flask --app panel.app init_db
docker compose exec stankin-antispam-bot flask --app panel.app init_admin
```

---

## Установка

### Локальная установка

#### Требования
- Python 3.11+
- pip

#### Шаги установки

```bash
# 1. Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# 2. Установка зависимостей
pip install --upgrade pip
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

# 3. Настройка переменных окружения
cp .env.example .env
# Отредактируйте .env файл

# 4. Инициализация базы данных
flask --app panel.app init_db

# 5. Создание администратора
# Убедитесь, что в .env задан ADMIN_PASSWORD
flask --app panel.app init_admin

# 6. Загрузка ML-моделей
# Скачайте модели из Releases и распакуйте в папку models/

# 7. Запуск
python run.py
```

### Docker

#### Требования
- Docker
- Docker Compose

#### Установка и запуск

```bash
# 1. Настройте переменные окружения
cp .env.example .env
# Отредактируйте .env файл

# 2. Соберите и запустите контейнер
docker compose up -d

# 3. Инициализируйте базу данных
docker compose exec stankin-antispam-bot flask --app panel.app init_db

# 4. Создайте администратора
docker compose exec stankin-antispam-bot flask --app panel.app init_admin

# 5. Проверьте логи
docker compose logs -f stankin-antispam-bot
```

#### Персистентные данные

Данные сохраняются в следующих директориях (монтируются как volumes):
- `./logs` — логи приложения
- `./instance` — база данных SQLite
- `./data` — собранные сообщения и другие данные
- `./models` — ML модели (read-only)

#### Полезные команды Docker

```bash
# Просмотр логов
docker compose logs -f

# Остановка
docker compose down

# Перезапуск
docker compose restart

# Выполнение команд внутри контейнера
docker compose exec stankin-antispam-bot bash
docker compose exec stankin-antispam-bot flask --app panel.app <command>
```

---

## Запуск

### Локальный запуск

```bash
# Запуск бота и панели (по умолчанию)
python run.py

# Только бот
python run.py --bot

# Только панель  
python run.py --panel

# Справка
python run.py --help
```

### Docker

```bash
# Запуск (уже настроен в docker-compose.yml)
docker compose up -d
```

---

## Конфигурация

### Системные настройки (.env)

Создайте файл `.env` в корне проекта на основе `.env.example`:

```ini
# TELEGRAM BOT
BOT_TOKEN=your_bot_token_here
TEST_BOT_TOKEN=your_test_bot_token_here
BOT_NAME=STANKIN_AntiSpam_Bot

# TELEGRAM CHATS
TARGET_CHAT_ID=-1001234567890
NOTIFICATION_CHAT_ID=-1001234567890
NOTIFICATION_CHAT_98_SPAM_THREAD=1
NOTIFICATION_CHAT_94_SPAM_THREAD=2
NOTIFICATION_CHAT_NS_SPAM_THREAD=3
NOTIFICATION_CHAT_MUTED_THREAD=4

# FLASK / WEB PANEL
SECRET_KEY=your-secret-key-here-generate-random-string
ADMIN_PASSWORD=your-admin-password-here
PANEL_PORT=12523
PERMANENT_SESSION_LIFETIME=60
REMEMBER_COOKIE_DURATION=10080

# PATHS
LOGS_DIR=logs
DATABASE_DIR=instance
MODELS_DIR=models
BERT_MODEL=models/finetuned_rubert_tiny2

# MODE
TESTING=false

# OPTIONAL
# OPENAI_API_KEY=sk-your-openai-api-key-here
HELPDESK_EMAIL=support@example.com
```

**Важно:**
- `SECRET_KEY` — сгенерируйте случайную строку (минимум 32 символа)
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```
- `ADMIN_PASSWORD` — пароль для входа в панель управления
- `BOT_TOKEN` — получите у [@BotFather](https://t.me/BotFather)

### Настройки через панель (хранятся в БД)

Эти настройки можно изменять через веб-панель без перезапуска:

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `BERT_THRESHOLD` | Порог классификации BERT (0-1) | 0.945 |
| `BERT_SURE_THRESHOLD` | Порог для авто-действий (0-1) | 0.98 |
| `CHECK_REPLY_MARKUP` | Проверять inline-клавиатуры | true |
| `CHECK_CAS` | Проверять через CAS API | true |
| `CHECK_LOLS` | Проверять через LOLS API | true |
| `ENABLE_CHATGPT` | Использовать ChatGPT | false |
| `ENABLE_DELETING` | Авто-удаление спама | true |
| `ENABLE_AUTOMUTING` | Авто-ограничение спамеров | false |
| `COLLECT_ALL_MESSAGES` | Сбор всех сообщений | false |
| `PER_PAGE` | Записей на странице | 10 |

---

## Первоначальная настройка

### Создание администратора

#### Локально

```bash
# 1. Убедитесь, что в .env задан ADMIN_PASSWORD
grep ADMIN_PASSWORD .env

# 2. Инициализируйте БД (если еще не сделано)
flask --app panel.app init_db

# 3. Создайте администратора
flask --app panel.app init_admin
```

#### В Docker

```bash
# 1. Убедитесь, что контейнер запущен
docker compose ps

# 2. Инициализируйте БД
docker compose exec stankin-antispam-bot flask --app panel.app init_db

# 3. Создайте администратора
docker compose exec stankin-antispam-bot flask --app panel.app init_admin
```

После создания администратора войдите в панель:
- URL: `http://localhost:12523` (или ваш `PANEL_PORT`)
- Имя: `admin`
- Пароль: значение из `ADMIN_PASSWORD` в `.env`

### Получение пароля для других пользователей

Администраторы чата могут получить пароль для панели через бота:

1. Отправьте боту команду `/get_password`
2. Бот проверит ваши права администратора в целевом чате
3. Вы получите имя пользователя и пароль для входа

---

## Архитектура

```
STANKIN_AntiSpam_Bot/
├── run.py                       # Единая точка входа
├── .env                         # Переменные окружения (не в Git)
├── .env.example                 # Пример конфигурации
├── docker-compose.yml           # Docker Compose конфигурация
├── Dockerfile                   # Docker образ
│
├── bot/                         # Telegram бот
│   ├── __init__.py
│   ├── core.py                  # Ядро: Bot, Dispatcher, константы
│   ├── database.py              # Операции с БД (aiosqlite)
│   ├── keyboards.py             # Построители клавиатур
│   ├── notifications.py         # Форматирование и отправка уведомлений
│   └── handlers/                # Обработчики событий
│       ├── commands.py          # Команды (/start, /code, /get_password)
│       ├── callbacks.py         # Callback-кнопки (mute, unmute, delete, not_spam)
│       └── messages.py          # Проверка сообщений на спам
│
├── panel/                       # Веб-панель управления
│   ├── app.py                   # Flask приложение
│   ├── auth.py                  # Аутентификация
│   ├── main.py                  # Основные маршруты
│   ├── db_models.py             # SQLAlchemy модели
│   ├── static/                  # CSS, JS, шрифты, изображения
│   │   ├── styles/
│   │   ├── scripts/
│   │   ├── images/
│   │   └── fonts/
│   └── templates/               # HTML шаблоны (Jinja2)
│
├── utils/                       # Утилиты
│   ├── config.py                # Системная конфигурация (из .env)
│   ├── logging.py               # Настройка логирования
│   ├── helpers.py               # Вспомогательные функции
│   ├── text.py                  # Обработка текста
│   ├── apis.py                  # Внешние API (CAS, LOLS)
│   └── ml.py                    # ML предсказания (BERT, ChatGPT)
│
├── models/                      # ML модели
│   └── finetuned_rubert_tiny2/
│
├── instance/                    # SQLite БД
│   └── db.sqlite
│
└── logs/                        # Логи
    └── YYYY-MM-DD_HH-MM-SS.log
```

### Хранение данных

| Данные | Хранилище | Описание |
|--------|-----------|----------|
| Системные настройки | `.env` | Требуют перезапуска для применения |
| Рантайм настройки | SQLite БД (`setting`) | Можно менять через панель |
| Спам-сообщения | SQLite БД (`spam_message`) | История обнаруженного спама |
| Ограниченные пользователи | SQLite БД (`muted_user`) | История ограничений |
| Белый список | SQLite БД (`whitelist_user`) | Пользователи, исключенные из проверки |
| Собранные сообщения | SQLite БД (`collected_message`) | Все сообщения (если включен сбор) |
| Пользователи панели | SQLite БД (`user`) | Учетные записи для веб-панели |

---

## Использование

### Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Начало работы с ботом |
| `/get_password` | Получить пароль для панели управления (только для администраторов чата) |
| `/code` | Ссылка на GitHub репозиторий |

### Веб-панель

1. Откройте `http://localhost:12523` (или ваш `PANEL_PORT`)
2. Войдите с учетными данными администратора
3. Просматривайте статистику и настраивайте параметры

**Страницы панели:**
- `/` — список обнаруженного спама
- `/muted` — ограниченные пользователи
- `/settings` — настройки системы (требует прав `can_configure`)

### Белый список пользователей

Если сообщение ошибочно помечено как спам:
1. Нажмите кнопку **"Не спам"** в уведомлении
2. Пользователь автоматически добавляется в белый список
3. Сообщения этого пользователя больше не проверяются на спам

### Уровни уверенности

- **98% и выше** (`BERT_SURE_THRESHOLD`) → Автоматическое удаление и ограничение
- **94-98%** → Уведомление с кнопками для ручной модерации
- **Ниже 94%** → Сообщение пропускается

---

## Flask CLI команды

```bash
# Инициализация БД (создание таблиц и настроек по умолчанию)
flask --app panel.app init_db

# Создание администратора
flask --app panel.app init_admin

# Создание тестового спам-сообщения
flask --app panel.app init_spam

# Создание тестового ограниченного пользователя
flask --app panel.app init_muted
```

---

## Технологии

### Backend
- **[Python 3.11+](https://www.python.org/)** — основной язык
- **[Aiogram 3](https://github.com/aiogram/aiogram)** — Telegram Bot API
- **[Flask](https://flask.palletsprojects.com/)** — веб-фреймворк
- **[SQLAlchemy](https://www.sqlalchemy.org/)** — ORM
- **[aiosqlite](https://github.com/omnilib/aiosqlite)** — асинхронный SQLite
- **[aiohttp](https://docs.aiohttp.org/)** — асинхронный HTTP клиент

### Machine Learning
- **[Transformers](https://huggingface.co/transformers/)** — NLP модели
- **[PyTorch](https://pytorch.org/)** — ML фреймворк
- **[scikit-learn](https://scikit-learn.org/)** — классические ML модели

### Frontend
- **HTML5/CSS3** — адаптивный дизайн
- **Vanilla JS** — интерактивность

### DevOps
- **[Docker](https://www.docker.com/)** — контейнеризация
- **[Waitress](https://docs.pylonsproject.org/projects/waitress/)** — WSGI сервер

---

<p align="center">
  Сделано для <a href="https://stankin.ru">МГТУ "СТАНКИН"</a>
</p>
