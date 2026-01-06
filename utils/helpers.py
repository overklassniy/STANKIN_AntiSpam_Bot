"""
Вспомогательные функции.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Union

from utils.logging import logger


def plural_form(number: int, singular: str, plural_genitive: str, plural_nominative: str) -> str:
    """
    Возвращает правильную форму слова в зависимости от числа.

    Примеры:
        plural_form(1, "запись", "записей", "записи") -> "запись"
        plural_form(2, "запись", "записей", "записи") -> "записи"
        plural_form(5, "запись", "записей", "записи") -> "записей"

    Args:
        number: Число
        singular: Форма для 1 (одна запись)
        plural_genitive: Форма для 5+ (пять записей)
        plural_nominative: Форма для 2-4 (две записи)

    Returns:
        Правильная форма слова
    """
    if 11 <= number % 100 <= 19:
        return plural_genitive
    elif number % 10 == 1:
        return singular
    elif 2 <= number % 10 <= 4:
        return plural_nominative
    else:
        return plural_genitive


def load_json_file(file_path: str, default_value: Union[Dict, List]) -> Union[Dict, List]:
    """
    Загружает данные из JSON файла.

    Args:
        file_path: Путь к файлу
        default_value: Значение по умолчанию, если файл не найден

    Returns:
        Данные из файла или значение по умолчанию
    """
    path = Path(file_path)
    if not path.exists():
        logger.warning(f"Файл {file_path} не найден. Используется значение по умолчанию.")
        return default_value

    try:
        with open(path, 'r', encoding='UTF-8') as f:
            data = json.load(f)
            logger.debug(f"Файл {file_path} успешно загружен.")
            return data
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка декодирования JSON в файле {file_path}: {e}")
        return default_value
    except Exception as e:
        logger.error(f"Ошибка при загрузке файла {file_path}: {e}")
        return default_value


def save_json_file(file_path: str, data: Union[Dict, List]) -> bool:
    """
    Сохраняет данные в JSON файл.

    Args:
        file_path: Путь к файлу
        data: Данные для сохранения

    Returns:
        True если успешно, False в случае ошибки
    """
    path = Path(file_path)

    # Создаем директорию если нужно
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(path, 'w', encoding='UTF-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        logger.debug(f"Данные сохранены в {file_path}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при сохранении файла {file_path}: {e}")
        return False


def get_pkl_files(directory: str) -> List[str]:
    """
    Возвращает список .pkl файлов в директории.

    Args:
        directory: Путь к директории

    Returns:
        Список имен .pkl файлов
    """
    path = Path(directory)
    if not path.is_dir():
        logger.error(f"Директория {directory} не существует")
        return []

    try:
        pkl_files = [f.name for f in path.glob('*.pkl')]
        logger.debug(f"Найдено {len(pkl_files)} .pkl файлов в {directory}")
        return pkl_files
    except Exception as e:
        logger.error(f"Ошибка при поиске файлов в {directory}: {e}")
        return []


def add_hours_get_timestamp(hours: int) -> float:
    """
    Добавляет указанное количество часов к текущему времени.

    Специальное значение 999 возвращает timestamp для 2100 года (перманентный бан).

    Args:
        hours: Количество часов (или 999 для перманентного ограничения)

    Returns:
        Unix timestamp
    """
    if hours == 999:
        return 4102455600.0  # 01.01.2100 00:00:00

    new_time = datetime.now() + timedelta(hours=hours)
    return new_time.timestamp()


def format_timestamp(timestamp: float, fmt: str = "%d.%m.%Y %H:%M:%S") -> str:
    """
    Форматирует Unix timestamp в строку.

    Args:
        timestamp: Unix timestamp
        fmt: Формат даты/времени

    Returns:
        Отформатированная строка
    """
    return datetime.fromtimestamp(timestamp).strftime(fmt)


def escape_html(text: str) -> str:
    """
    Экранирует HTML-символы в тексте.

    Args:
        text: Исходный текст

    Returns:
        Текст с экранированными HTML-символами
    """
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
