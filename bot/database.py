"""
Модуль для работы с базой данных (асинхронный SQLite).

Содержит все операции с БД для бота.
"""

import os
from datetime import datetime
from typing import Any, Dict, Optional

import aiosqlite

from utils.config import DATABASE_DIR, DATABASE_PATH, DEFAULT_SETTINGS

# Локальный кэш настроек
_settings_cache: Dict[str, Any] = {}
_cache_loaded: bool = False


async def get_connection() -> aiosqlite.Connection:
    """Создает подключение к базе данных."""
    return await aiosqlite.connect(DATABASE_PATH)


async def init_database() -> None:
    """
    Инициализирует базу данных, создавая необходимые таблицы.
    """
    os.makedirs(DATABASE_DIR, exist_ok=True)

    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Таблица пользователей (для авторизации в панели)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS user (
                id INTEGER PRIMARY KEY,
                name VARCHAR(1000),
                password VARCHAR(1000),
                can_configure BOOLEAN DEFAULT 0
            )
        ''')

        # Таблица спам-сообщений
        await db.execute('''
            CREATE TABLE IF NOT EXISTS spam_message (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp FLOAT NOT NULL,
                author_id BIGINT NOT NULL,
                author_username VARCHAR(255),
                message_text TEXT NOT NULL,
                has_reply_markup BOOLEAN,
                cas BOOLEAN,
                lols BOOLEAN,
                chatgpt_prediction FLOAT,
                bert_prediction FLOAT
            )
        ''')

        # Таблица ограниченных пользователей
        await db.execute('''
            CREATE TABLE IF NOT EXISTS muted_user (
                id INTEGER PRIMARY KEY,
                username VARCHAR(255),
                timestamp FLOAT NOT NULL,
                muted_till_timestamp FLOAT,
                relapse_number INTEGER DEFAULT 0
            )
        ''')

        # Таблица настроек
        await db.execute('''
            CREATE TABLE IF NOT EXISTS setting (
                key VARCHAR(100) PRIMARY KEY,
                value TEXT NOT NULL,
                value_type VARCHAR(20) NOT NULL DEFAULT 'str',
                description VARCHAR(500)
            )
        ''')

        # Таблица собранных сообщений
        await db.execute('''
            CREATE TABLE IF NOT EXISTS collected_message (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp FLOAT NOT NULL,
                chat_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                username VARCHAR(255),
                message_text TEXT NOT NULL
            )
        ''')

        # Таблица белого списка пользователей
        await db.execute('''
            CREATE TABLE IF NOT EXISTS whitelist_user (
                id INTEGER PRIMARY KEY,
                username VARCHAR(255),
                added_at FLOAT NOT NULL,
                added_by BIGINT,
                reason TEXT
            )
        ''')

        await db.commit()

        # Инициализация настроек по умолчанию
        await init_default_settings(db)


async def init_default_settings(db: aiosqlite.Connection) -> None:
    """Инициализирует настройки по умолчанию, если их нет."""
    descriptions = {
        'BERT_THRESHOLD': 'Порог классификации BERT (0-1)',
        'BERT_SURE_THRESHOLD': 'Порог уверенности для авто-действий (0-1)',
        'CHECK_REPLY_MARKUP': 'Проверять наличие inline-клавиатуры',
        'CHECK_CAS': 'Проверять пользователей через CAS API',
        'CHECK_LOLS': 'Проверять пользователей через LOLS API',
        'ENABLE_CHATGPT': 'Использовать ChatGPT для анализа',
        'ENABLE_DELETING': 'Автоматически удалять спам',
        'ENABLE_AUTOMUTING': 'Автоматически ограничивать спамеров',
        'COLLECT_ALL_MESSAGES': 'Собирать все сообщения для анализа',
        'PER_PAGE': 'Записей на странице в панели',
    }

    for key, value in DEFAULT_SETTINGS.items():
        # Проверяем, существует ли настройка
        async with db.execute('SELECT key FROM setting WHERE key = ?', (key,)) as cursor:
            if await cursor.fetchone() is None:
                # Определяем тип
                if isinstance(value, bool):
                    value_type = 'bool'
                    str_value = 'true' if value else 'false'
                elif isinstance(value, int):
                    value_type = 'int'
                    str_value = str(value)
                elif isinstance(value, float):
                    value_type = 'float'
                    str_value = str(value)
                else:
                    value_type = 'str'
                    str_value = str(value)

                await db.execute(
                    'INSERT INTO setting (key, value, value_type, description) VALUES (?, ?, ?, ?)',
                    (key, str_value, value_type, descriptions.get(key, ''))
                )

    await db.commit()


# Settings Operations
async def get_setting(key: str, default: Any = None) -> Any:
    """
    Получает значение настройки из БД.

    Args:
        key: Ключ настройки
        default: Значение по умолчанию

    Returns:
        Значение настройки с правильным типом
    """
    global _settings_cache, _cache_loaded

    # Загружаем кэш при первом обращении
    if not _cache_loaded:
        await reload_settings_cache()

    if key in _settings_cache:
        return _settings_cache[key]

    return default


async def reload_settings_cache() -> None:
    """Перезагружает кэш настроек из БД."""
    global _settings_cache, _cache_loaded

    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute('SELECT key, value, value_type FROM setting') as cursor:
            _settings_cache = {}
            async for row in cursor:
                key, value, value_type = row
                if value_type == 'bool':
                    _settings_cache[key] = value.lower() in ('true', '1', 'yes')
                elif value_type == 'int':
                    _settings_cache[key] = int(value)
                elif value_type == 'float':
                    _settings_cache[key] = float(value)
                else:
                    _settings_cache[key] = value
            _cache_loaded = True


async def get_all_settings() -> Dict[str, Any]:
    """Получает все настройки."""
    global _settings_cache, _cache_loaded

    if not _cache_loaded:
        await reload_settings_cache()

    return _settings_cache.copy()


async def update_setting(key: str, value: Any) -> None:
    """Обновляет значение настройки."""
    global _settings_cache

    # Определяем тип
    if isinstance(value, bool):
        value_type = 'bool'
        str_value = 'true' if value else 'false'
    elif isinstance(value, int):
        value_type = 'int'
        str_value = str(value)
    elif isinstance(value, float):
        value_type = 'float'
        str_value = str(value)
    else:
        value_type = 'str'
        str_value = str(value)

    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            '''INSERT OR REPLACE INTO setting (key, value, value_type) 
               VALUES (?, ?, ?)''',
            (key, str_value, value_type)
        )
        await db.commit()

    # Обновляем кэш
    if isinstance(value, bool):
        _settings_cache[key] = value
    elif isinstance(value, int):
        _settings_cache[key] = value
    elif isinstance(value, float):
        _settings_cache[key] = value
    else:
        _settings_cache[key] = str_value


# User Operations
async def get_user_by_id(user_id: int) -> Optional[dict]:
    """Получает пользователя по ID."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM user WHERE id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def create_user(user_id: int, name: str, password_hash: str, can_configure: bool = False) -> None:
    """Создает нового пользователя."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            'INSERT INTO user (id, name, password, can_configure) VALUES (?, ?, ?, ?)',
            (user_id, name, password_hash, can_configure)
        )
        await db.commit()


async def update_user_password(user_id: int, password_hash: str) -> None:
    """Обновляет пароль пользователя."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            'UPDATE user SET password = ? WHERE id = ?',
            (password_hash, user_id)
        )
        await db.commit()


async def create_or_update_user(user_id: int, name: str, password_hash: str, can_configure: bool = False) -> None:
    """Создает или обновляет пользователя."""
    existing = await get_user_by_id(user_id)
    if existing:
        await update_user_password(user_id, password_hash)
    else:
        await create_user(user_id, name, password_hash, can_configure)


# Muted User Operations
async def get_muted_user(user_id: int) -> Optional[dict]:
    """Получает информацию об ограниченном пользователе."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM muted_user WHERE id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def create_muted_user(
    user_id: int,
    username: Optional[str],
    timestamp: float,
    muted_till_timestamp: Optional[float],
    relapse_number: int = 1
) -> None:
    """Создает запись об ограниченном пользователе."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            '''INSERT INTO muted_user (id, username, timestamp, muted_till_timestamp, relapse_number) 
               VALUES (?, ?, ?, ?, ?)''',
            (user_id, username, timestamp, muted_till_timestamp, relapse_number)
        )
        await db.commit()


async def update_muted_user(
    user_id: int,
    timestamp: float,
    muted_till_timestamp: Optional[float],
    relapse_number: int
) -> None:
    """Обновляет запись об ограниченном пользователе."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            '''UPDATE muted_user SET timestamp = ?, muted_till_timestamp = ?, relapse_number = ?
               WHERE id = ?''',
            (timestamp, muted_till_timestamp, relapse_number, user_id)
        )
        await db.commit()


async def clear_muted_user_timestamp(user_id: int) -> None:
    """Очищает время ограничения пользователя."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            'UPDATE muted_user SET muted_till_timestamp = NULL WHERE id = ?',
            (user_id,)
        )
        await db.commit()


# Spam Message Operations
async def add_spam_message(
    timestamp: float,
    author_id: int,
    author_username: Optional[str],
    message_text: str,
    has_reply_markup: Optional[bool],
    cas: Optional[bool],
    lols: Optional[bool],
    chatgpt_prediction: Optional[float],
    bert_prediction: float
) -> None:
    """Добавляет запись о спам-сообщении."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            '''INSERT INTO spam_message (timestamp, author_id, author_username, message_text,
               has_reply_markup, cas, lols, chatgpt_prediction, bert_prediction)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (timestamp, author_id, author_username, message_text,
             has_reply_markup, cas, lols, chatgpt_prediction, bert_prediction)
        )
        await db.commit()


# Collected Message Operations
async def add_collected_message(
    chat_id: int,
    user_id: int,
    username: Optional[str],
    message_text: str
) -> None:
    """Добавляет собранное сообщение в БД."""
    timestamp = datetime.now().timestamp()

    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            '''INSERT INTO collected_message (timestamp, chat_id, user_id, username, message_text)
               VALUES (?, ?, ?, ?, ?)''',
            (timestamp, chat_id, user_id, username, message_text)
        )
        await db.commit()


async def get_collected_messages_count() -> int:
    """Возвращает количество собранных сообщений."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute('SELECT COUNT(*) FROM collected_message') as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


# Whitelist Operations
async def is_whitelisted(user_id: int) -> bool:
    """Проверяет, находится ли пользователь в белом списке."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute('SELECT id FROM whitelist_user WHERE id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row is not None


async def add_to_whitelist(
    user_id: int,
    username: Optional[str],
    added_by: Optional[int] = None,
    reason: Optional[str] = None
) -> None:
    """Добавляет пользователя в белый список."""
    timestamp = datetime.now().timestamp()

    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Проверяем, не добавлен ли уже
        if await is_whitelisted(user_id):
            return

        await db.execute(
            '''INSERT INTO whitelist_user (id, username, added_at, added_by, reason)
               VALUES (?, ?, ?, ?, ?)''',
            (user_id, username, timestamp, added_by, reason)
        )
        await db.commit()


async def remove_from_whitelist(user_id: int) -> None:
    """Удаляет пользователя из белого списка."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('DELETE FROM whitelist_user WHERE id = ?', (user_id,))
        await db.commit()
