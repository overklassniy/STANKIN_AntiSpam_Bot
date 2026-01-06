# СТАНКИН Анти-спам система

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

Комплексное решение для борьбы со спамом в Telegram-чатах.

## Возможности

- **Telegram-бот** для мониторинга и модерации
- **Веб-панель** для настройки и статистики
- **ML-модели** (RuBERT) для классификации спама
- **Интеграции** с CAS, LOLS, ChatGPT

---

## Быстрый старт

```bash
# 1. Клонируйте репозиторий
git clone https://github.com/overklassniy/STANKIN_AntiSpam_Bot.git
cd STANKIN_AntiSpam_Bot

# 2. Настройте переменные окружения
# Создайте .env файл (см. раздел Конфигурация)

# 3. Запустите через Docker
docker compose up -d
```

---

## Установка

### Локальная установка

```bash
# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Установка зависимостей
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

# Инициализация БД
flask --app panel.app init_db
flask --app panel.app init_admin

# Запуск
python run.py
```

### Docker

```bash
docker compose up -d
```

---

## Запуск

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

---

## Конфигурация

### Системные настройки (.env)

Создайте файл `.env` в корне проекта:

```ini
# Telegram
BOT_TOKEN=your_bot_token
BOT_NAME=your_bot_username
TARGET_CHAT_ID=-1001234567890
NOTIFICATION_CHAT_ID=-1001234567890
NOTIFICATION_CHAT_98_SPAM_THREAD=1
NOTIFICATION_CHAT_94_SPAM_THREAD=2
NOTIFICATION_CHAT_NS_SPAM_THREAD=3
NOTIFICATION_CHAT_MUTED_THREAD=4

# Flask
SECRET_KEY=your-secret-key
ADMIN_PASSWORD=admin-password
PANEL_PORT=12523

# Paths
LOGS_DIR=logs
DATABASE_DIR=instance
MODELS_DIR=models
BERT_MODEL=models/finetuned_rubert_tiny2

# Mode
TESTING=false

# Optional
OPENAI_API_KEY=sk-...
HELPDESK_EMAIL=support@example.com
```

### Настройки через панель (хранятся в БД)

| Параметр | Описание |
|----------|----------|
| `BERT_THRESHOLD` | Порог классификации BERT (0-1) |
| `BERT_SURE_THRESHOLD` | Порог для авто-действий (0-1) |
| `CHECK_REPLY_MARKUP` | Проверять inline-клавиатуры |
| `CHECK_CAS` | Проверять через CAS API |
| `CHECK_LOLS` | Проверять через LOLS API |
| `ENABLE_CHATGPT` | Использовать ChatGPT |
| `ENABLE_DELETING` | Авто-удаление спама |
| `ENABLE_AUTOMUTING` | Авто-ограничение спамеров |
| `COLLECT_ALL_MESSAGES` | Сбор всех сообщений |
| `PER_PAGE` | Записей на странице |

---

## Архитектура

```
STANKIN_AntiSpam_Bot/
├── run.py                  # Единая точка входа
│
├── bot/                    # Telegram бот
│   ├── core.py             # Ядро бота
│   ├── database.py         # Операции с БД
│   ├── keyboards.py        # Клавиатуры
│   ├── notifications.py    # Уведомления
│   └── handlers/           # Обработчики
│       ├── commands.py
│       ├── callbacks.py
│       └── messages.py
│
├── panel/                  # Веб-панель
│   ├── app.py
│   ├── auth.py
│   ├── main.py
│   └── db_models.py
│
├── utils/                  # Утилиты
│   ├── config.py           # Системная конфигурация
│   ├── logging.py
│   ├── helpers.py
│   ├── text.py
│   ├── apis.py
│   └── ml.py
│
├── models/                 # ML модели
├── instance/               # SQLite БД
└── logs/                   # Логи
```

### Хранение данных

| Данные | Хранилище |
|--------|-----------|
| Системные настройки | `.env` / переменные окружения |
| Рантайм настройки | SQLite БД (таблица `setting`) |
| Спам-сообщения | SQLite БД (таблица `spam_message`) |
| Ограниченные пользователи | SQLite БД (таблица `muted_user`) |
| Собранные сообщения | SQLite БД (таблица `collected_message`) |
| Пользователи панели | SQLite БД (таблица `user`) |

---

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Начало работы |
| `/get_password` | Получить пароль для панели |
| `/code` | Ссылка на GitHub |

---

## Технологии

- **Python 3.11+**
- **Aiogram 3** — Telegram Bot API
- **Flask** + **SQLAlchemy** — веб-панель
- **aiosqlite** — асинхронный SQLite
- **Transformers** + **PyTorch** — ML
- **Docker** — контейнеризация

---

<p align="center">
  Сделано для <a href="https://stankin.ru">МГТУ "СТАНКИН"</a>
</p>
