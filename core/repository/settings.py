"""Репозиторий настроек: глобальные и per-chat."""

from typing import Any, Dict, Optional

from core.db import get_pool
from core.config import DEFAULT_SETTINGS

SETTING_DESCRIPTIONS = {
    'BERT_MODEL': 'Используемая BERT модель из директории models',
    'BERT_THRESHOLD': 'Порог классификации BERT (0-1)',
    'BERT_SURE_THRESHOLD': 'Порог уверенности для авто-действий (0-1)',
    'CHECK_REPLY_MARKUP': 'Проверять наличие inline-клавиатуры',
    'CHECK_CAS': 'Проверять пользователей через CAS API',
    'CHECK_LOLS': 'Проверять пользователей через LOLS API',
    'CHECK_EMAIL_NOT_SURE': 'Помечать сообщения с email как NOT SURE',
    'ENABLE_CHATGPT': 'Использовать ChatGPT для анализа',
    'ENABLE_DELETING': 'Автоматически удалять спам',
    'ENABLE_AUTOMUTING': 'Автоматически ограничивать спамеров',
    'COLLECT_ALL_MESSAGES': 'Собирать все сообщения для анализа',
    'PER_PAGE': 'Записей на странице в панели',
}


def _cast_value(value: str, value_type: str) -> Any:
    """Преобразует строковое значение в нужный тип.

    Аргументы:
        value (str): Строковое значение.
        value_type (str): Тип: bool, int, float или str.

    Возвращаемое значение:
        result (Any): Преобразованное значение.
    """
    if value_type == 'bool':
        return value.lower() in ('true', '1', 'yes')
    elif value_type == 'int':
        try:
            return int(value)
        except ValueError:
            if value.lower() in ('true', 'false'):
                return value.lower() == 'true'
            return value
    elif value_type == 'float':
        try:
            return float(value)
        except ValueError:
            if value.lower() in ('true', 'false'):
                return value.lower() == 'true'
            return value
    return value


def _detect_type(value: Any) -> str:
    """Определяет тип значения для записи в БД.

    Аргументы:
        value (Any): Значение для анализа.

    Возвращаемое значение:
        type_name (str): Имя типа: bool, int, float или str.
    """
    if isinstance(value, bool):
        return 'bool'
    elif isinstance(value, int):
        return 'int'
    elif isinstance(value, float):
        return 'float'
    return 'str'


class SettingsRepository:
    """Репозиторий для работы с настройками системы."""

    # Глобальные настройки

    @staticmethod
    async def get_global(key: str, default: Any = None) -> Any:
        """Получает глобальную настройку.

        Аргументы:
            key (str): Ключ настройки.
            default (Any): Значение по умолчанию.

        Возвращаемое значение:
            value (Any): Значение настройки с правильным типом.
        """
        pool = get_pool()
        row = await pool.fetchrow(
            'SELECT value, value_type FROM global_setting WHERE key = $1', key
        )
        if row:
            return _cast_value(row['value'], row['value_type'])
        return DEFAULT_SETTINGS.get(key, default)

    @staticmethod
    async def get_all_global() -> Dict[str, Any]:
        """Получает все глобальные настройки.

        Возвращаемое значение:
            settings (Dict[str, Any]): Словарь всех настроек.
        """
        pool = get_pool()
        rows = await pool.fetch('SELECT key, value, value_type FROM global_setting')
        result = {}
        for row in rows:
            result[row['key']] = _cast_value(row['value'], row['value_type'])
        return result

    @staticmethod
    async def update_global(key: str, value: Any) -> None:
        """Обновляет глобальную настройку.

        Аргументы:
            key (str): Ключ настройки.
            value (Any): Новое значение.
        """
        pool = get_pool()
        value_type = _detect_type(value)
        str_value = str(value)
        if value_type == 'bool':
            str_value = 'true' if value else 'false'

        await pool.execute(
            '''INSERT INTO global_setting (key, value, value_type, description)
               VALUES ($1, $2, $3, $4)
               ON CONFLICT (key) DO UPDATE SET value = $2, value_type = $3''',
            key, str_value, value_type,
            SETTING_DESCRIPTIONS.get(key, '')
        )

    @staticmethod
    async def init_default_global_settings() -> None:
        """Инициализирует глобальные настройки по умолчанию, если их нет."""
        pool = get_pool()
        for key, value in DEFAULT_SETTINGS.items():
            value_type = _detect_type(value)
            str_value = ('true' if value else 'false') if value_type == 'bool' else str(value)
            await pool.execute(
                '''INSERT INTO global_setting (key, value, value_type, description)
                   VALUES ($1, $2, $3, $4)
                   ON CONFLICT (key) DO NOTHING''',
                key, str_value, value_type,
                SETTING_DESCRIPTIONS.get(key, '')
            )

    # Per-chat настройки

    @staticmethod
    async def get_chat_setting(chat_pk: int, key: str, default: Any = None) -> Any:
        """Получает per-chat настройку с fallback на глобальную.

        Аргументы:
            chat_pk (int): PK чата в таблице chat.
            key (str): Ключ настройки.
            default (Any): Значение по умолчанию, если нет ни per-chat, ни глобальной.

        Возвращаемое значение:
            value (Any): Значение настройки.
        """
        pool = get_pool()
        row = await pool.fetchrow(
            'SELECT value, value_type FROM chat_setting WHERE chat_id = $1 AND key = $2',
            chat_pk, key
        )
        if row:
            return _cast_value(row['value'], row['value_type'])
        return await SettingsRepository.get_global(key, default)

    @staticmethod
    async def get_all_chat_settings(chat_pk: int) -> Dict[str, Any]:
        """Получает все настройки для чата (per-chat + fallback на глобальные).

        Аргументы:
            chat_pk (int): PK чата в таблице chat.

        Возвращаемое значение:
            settings (Dict[str, Any]): Словарь настроек.
        """
        pool = get_pool()
        rows = await pool.fetch(
            'SELECT key, value, value_type FROM chat_setting WHERE chat_id = $1', chat_pk
        )
        chat_settings = {}
        for row in rows:
            chat_settings[row['key']] = _cast_value(row['value'], row['value_type'])

        global_settings = await SettingsRepository.get_all_global()

        result = dict(global_settings)
        result.update(chat_settings)
        return result

    @staticmethod
    async def update_chat_setting(chat_pk: int, key: str, value: Any) -> None:
        """Обновляет per-chat настройку.

        Аргументы:
            chat_pk (int): PK чата.
            key (str): Ключ настройки.
            value (Any): Новое значение.
        """
        pool = get_pool()
        value_type = _detect_type(value)
        str_value = ('true' if value else 'false') if value_type == 'bool' else str(value)

        await pool.execute(
            '''INSERT INTO chat_setting (chat_id, key, value, value_type, description)
               VALUES ($1, $2, $3, $4, $5)
               ON CONFLICT (chat_id, key) DO UPDATE SET value = $3, value_type = $4''',
            chat_pk, key, str_value, value_type,
            SETTING_DESCRIPTIONS.get(key, '')
        )
