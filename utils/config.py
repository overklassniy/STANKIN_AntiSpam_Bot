"""
Системная конфигурация приложения.

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

# Директория для базы данных (абсолютный путь)
DATABASE_DIR = str(BASE_DIR / os.getenv('DATABASE_DIR', 'instance'))

# Путь к базе данных SQLite (абсолютный путь)
DATABASE_PATH = str(Path(DATABASE_DIR) / 'db.sqlite')

# Директория с ML моделями (абсолютный путь)
MODELS_DIR = str(BASE_DIR / os.getenv('MODELS_DIR', 'models'))

# Путь к BERT модели
BERT_MODEL = os.getenv('BERT_MODEL', str(Path(MODELS_DIR) / 'finetuned_rubert_tiny2'))


# TELEGRAM НАСТРОЙКИ
# Режим тестирования
TESTING = os.getenv('TESTING', 'false').lower() in ('true', '1', 'yes')

# Имя бота (без @)
BOT_NAME = os.getenv('BOT_NAME', 'STANKIN_AntiSpam_Bot')

# ID целевого чата для модерации
TARGET_CHAT_ID = int(os.getenv('TARGET_CHAT_ID', '0'))

# ID чата для уведомлений
NOTIFICATION_CHAT_ID = int(os.getenv('NOTIFICATION_CHAT_ID', '0'))

# ID тредов для уведомлений
NOTIFICATION_CHAT_98_SPAM_THREAD = int(os.getenv('NOTIFICATION_CHAT_98_SPAM_THREAD', '1'))
NOTIFICATION_CHAT_94_SPAM_THREAD = int(os.getenv('NOTIFICATION_CHAT_94_SPAM_THREAD', '2'))
NOTIFICATION_CHAT_NS_SPAM_THREAD = int(os.getenv('NOTIFICATION_CHAT_NS_SPAM_THREAD', '3'))
NOTIFICATION_CHAT_MUTED_THREAD = int(os.getenv('NOTIFICATION_CHAT_MUTED_THREAD', '4'))

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
# Секретный ключ Flask
SECRET_KEY: Optional[str] = os.getenv('SECRET_KEY')

# Пароль администратора
ADMIN_PASSWORD: Optional[str] = os.getenv('ADMIN_PASSWORD')

# Email технической поддержки
HELPDESK_EMAIL = os.getenv('HELPDESK_EMAIL', 'support@example.com')


# ТОКЕНЫ
def get_bot_token() -> str:
    """Возвращает токен бота в зависимости от режима."""
    token_name = 'TEST_BOT_TOKEN' if TESTING else 'BOT_TOKEN'
    token = os.getenv(token_name)
    if not token:
        raise ValueError(f"Токен {token_name} не задан в переменных окружения!")
    return token


# ЗНАЧЕНИЯ ПО УМОЛЧАНИЮ ДЛЯ НАСТРОЕК В БД
DEFAULT_SETTINGS = {
    # Пороги BERT
    'BERT_THRESHOLD': 0.945,
    'BERT_SURE_THRESHOLD': 0.98,

    # Проверки
    'CHECK_REPLY_MARKUP': True,
    'CHECK_CAS': True,
    'CHECK_LOLS': True,
    'ENABLE_CHATGPT': False,

    # Действия
    'ENABLE_DELETING': True,
    'ENABLE_AUTOMUTING': False,
    'COLLECT_ALL_MESSAGES': False,

    # UI
    'PER_PAGE': 10,
}


# ССЫЛКИ
GITHUB_URL = 'https://github.com/overklassniy/STANKIN_AntiSpam_Bot/'


# ОБРАТНАЯ СОВМЕСТИМОСТЬ
# Словарь для обратной совместимости с кодом, использующим config['KEY']
class ConfigDict(dict):
    """Словарь с поддержкой получения системных настроек и настроек из БД."""

    def __getitem__(self, key):
        # Сначала проверяем системные настройки
        if hasattr(_module, key):
            return getattr(_module, key)
        # Затем значения по умолчанию
        if key in DEFAULT_SETTINGS:
            return DEFAULT_SETTINGS[key]
        return super().__getitem__(key)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default


_module = __import__(__name__)
config = ConfigDict()
