"""Системная конфигурация приложения.

Этот модуль содержит константы, которые НЕ могут быть изменены
через панель управления. Для изменения требуется перезапуск приложения.

Настройки, изменяемые через панель, хранятся в базе данных.
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()


# ПУТИ И ДИРЕКТОРИИ
# Корневая директория проекта (абсолютный путь)
BASE_DIR = Path(__file__).resolve().parent.parent

# Директория для логов (абсолютный путь)
LOGS_DIR = str(BASE_DIR / os.getenv('LOGS_DIR', 'logs'))

# Директория с ML моделями (абсолютный путь)
MODELS_DIR = str(BASE_DIR / os.getenv('MODELS_DIR', 'models'))

# Директория со сжатыми BERT-моделями (fp16, int8, onnx)
COMPRESSED_MODELS_DIR = str(Path(MODELS_DIR) / 'compressed')

# Путь к BERT модели
BERT_MODEL = os.getenv('BERT_MODEL', str(Path(MODELS_DIR) / 'finetuned_rubert_tiny2'))


# БАЗА ДАННЫХ
# Строка подключения к PostgreSQL
DATABASE_URL = os.getenv('DATABASE_URL')


# ПРОКСИ
# SOCKS5 прокси для Telegram Bot API (опционально)
PROXY_URL: Optional[str] = os.getenv('PROXY_URL')


# МОНИТОРИНГ
# DSN для Sentry (опционально, для мониторинга ошибок)
SENTRY_DSN: Optional[str] = os.getenv('SENTRY_DSN')


# TELEGRAM НАСТРОЙКИ
# Режим тестирования
TESTING = os.getenv('TESTING', 'false').lower() in ('true', '1', 'yes')

# Версия приложения (используется для Sentry release)
APP_VERSION = '3.0.0'

# ID чата для уведомлений (чат управления)
NOTIFICATION_CHAT_ID = int(os.getenv('NOTIFICATION_CHAT_ID', '0'))

# ID тредов для уведомлений
NOTIFICATION_CHAT_98_SPAM_THREAD = int(os.getenv('NOTIFICATION_CHAT_98_SPAM_THREAD', '1'))
NOTIFICATION_CHAT_94_SPAM_THREAD = int(os.getenv('NOTIFICATION_CHAT_94_SPAM_THREAD', '2'))
NOTIFICATION_CHAT_NS_SPAM_THREAD = int(os.getenv('NOTIFICATION_CHAT_NS_SPAM_THREAD', '3'))
NOTIFICATION_CHAT_MUTED_THREAD = int(os.getenv('NOTIFICATION_CHAT_MUTED_THREAD', '4'))

# ID треда для отправки резервных копий базы данных
NOTIFICATION_CHAT_BACKUP_THREAD = int(os.getenv('NOTIFICATION_CHAT_BACKUP_THREAD', '5'))

# Системные пользователи Telegram (анонимный админ, бот канала)
SYSTEM_USER_IDS = [777000, 1087968824]


# ВЕБ-ПАНЕЛЬ
# Порт панели управления
PANEL_PORT = int(os.getenv('PANEL_PORT', '12523'))

# Время жизни сессии (минуты)
PERMANENT_SESSION_LIFETIME = int(os.getenv('PERMANENT_SESSION_LIFETIME', '60'))

# Время жизни cookie "Запомнить меня" (минуты)
REMEMBER_COOKIE_DURATION = int(os.getenv('REMEMBER_COOKIE_DURATION', '10080'))


# БЕЗОПАСНОСТЬ
# Секретный ключ для подписи сессий и JWT
SECRET_KEY: Optional[str] = os.getenv('SECRET_KEY')

# Пароль администратора (используется только при первичной инициализации)
ADMIN_PASSWORD: Optional[str] = os.getenv('ADMIN_PASSWORD')

# Email технической поддержки
HELPDESK_EMAIL = os.getenv('HELPDESK_EMAIL', 'support@example.com')

# Процент трейс-сессий для Sentry (0.0–1.0)
SENTRY_TRACES_SAMPLE_RATE = float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', '1.0'))

# Включить отправку логов в Sentry (true/false)
SENTRY_ENABLE_LOGS = os.getenv('SENTRY_ENABLE_LOGS', 'false').lower() in ('true', '1', 'yes')

# Уровень логов, отправляемых в Sentry как structured logs
SENTRY_LOGS_LEVEL = os.getenv('SENTRY_LOGS_LEVEL', 'INFO').upper()

# Уровень логов, записываемых как breadcrumbs
SENTRY_BREADCRUMBS_LEVEL = os.getenv('SENTRY_BREADCRUMBS_LEVEL', 'INFO').upper()

# Уровень логов, отправляемых как events
SENTRY_EVENT_LEVEL = os.getenv('SENTRY_EVENT_LEVEL', 'ERROR').upper()


# ТОКЕНЫ
def get_bot_token() -> str:
    """Возвращает токен бота в зависимости от режима.

    Возвращаемое значение:
        token (str): Токен бота из переменной окружения.

    Исключения:
        ValueError: Если токен не задан в переменных окружения.
    """
    token_name = 'TEST_BOT_TOKEN' if TESTING else 'BOT_TOKEN'
    token = os.getenv(token_name)
    if not token:
        raise ValueError(f"Токен {token_name} не задан в переменных окружения!")
    return token


# ЗНАЧЕНИЯ ПО УМОЛЧАНИЮ ДЛЯ НАСТРОЕК В БД
DEFAULT_SETTINGS = {
    # Модель
    'BERT_MODEL': 'finetuned_rubert_tiny2_raw',

    # Пороги BERT
    'BERT_THRESHOLD': 0.945,
    'BERT_SURE_THRESHOLD': 0.98,

    # Проверки
    'CHECK_REPLY_MARKUP': True,
    'CHECK_CAS': True,
    'CHECK_LOLS': True,
    'CHECK_EMAIL_NOT_SURE': True,
    'ENABLE_CHATGPT': False,

    # Действия
    'ENABLE_DELETING': True,
    'ENABLE_AUTOMUTING': False,
    'COLLECT_ALL_MESSAGES': False,

    # UI
    'PER_PAGE': 10,

    # Резервное копирование
    'BACKUP_ENABLED': False,
    'BACKUP_START_TIME': '03:00',
    'BACKUP_INTERVAL_HOURS': 24,
}


# ССЫЛКИ
GITHUB_URL = 'https://github.com/overklassniy/STANKIN_AntiSpam_Bot/'
