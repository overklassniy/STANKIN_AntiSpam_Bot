"""
Утилиты для STANKIN AntiSpam System.

Модули:
- config: Системная конфигурация
- logging: Логирование
- helpers: Вспомогательные функции
- text: Обработка текста
- apis: Внешние API (CAS, LOLS)
- ml: Машинное обучение (BERT, ChatGPT)
"""

from utils.config import (
    BASE_DIR,
    LOGS_DIR,
    DATABASE_DIR,
    DATABASE_PATH,
    MODELS_DIR,
    BERT_MODEL,
    TESTING,
    BOT_NAME,
    TARGET_CHAT_ID,
    NOTIFICATION_CHAT_ID,
    NOTIFICATION_CHAT_98_SPAM_THREAD,
    NOTIFICATION_CHAT_94_SPAM_THREAD,
    NOTIFICATION_CHAT_NS_SPAM_THREAD,
    NOTIFICATION_CHAT_MUTED_THREAD,
    SYSTEM_USER_IDS,
    PANEL_PORT,
    SECRET_KEY,
    HELPDESK_EMAIL,
    GITHUB_URL,
    DEFAULT_SETTINGS,
    get_bot_token,
)

from utils.logging import logger, setup_logger

from utils.helpers import (
    plural_form,
    load_json_file,
    save_json_file,
    get_pkl_files,
    add_hours_get_timestamp,
    format_timestamp,
    escape_html,
)

__all__ = [
    # Config
    'BASE_DIR',
    'LOGS_DIR',
    'DATABASE_DIR',
    'DATABASE_PATH',
    'MODELS_DIR',
    'BERT_MODEL',
    'TESTING',
    'BOT_NAME',
    'TARGET_CHAT_ID',
    'NOTIFICATION_CHAT_ID',
    'NOTIFICATION_CHAT_98_SPAM_THREAD',
    'NOTIFICATION_CHAT_94_SPAM_THREAD',
    'NOTIFICATION_CHAT_NS_SPAM_THREAD',
    'NOTIFICATION_CHAT_MUTED_THREAD',
    'SYSTEM_USER_IDS',
    'PANEL_PORT',
    'SECRET_KEY',
    'HELPDESK_EMAIL',
    'GITHUB_URL',
    'DEFAULT_SETTINGS',
    'get_bot_token',
    # Logging
    'logger',
    'setup_logger',
    # Helpers
    'plural_form',
    'load_json_file',
    'save_json_file',
    'get_pkl_files',
    'add_hours_get_timestamp',
    'format_timestamp',
    'escape_html',
]
