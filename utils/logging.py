"""
Модуль настройки логирования.
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Импортируем config после его определения, чтобы избежать циклического импорта
_logger_instance: Optional[logging.Logger] = None


def setup_logger(
    logs_dir: str = 'logs',
    log_level: int = logging.INFO,
    log_format: str = '%(asctime)s - %(levelname)s - %(message)s'
) -> logging.Logger:
    """
    Настраивает и возвращает логгер.

    Args:
        logs_dir: Директория для файлов логов
        log_level: Уровень логирования
        log_format: Формат сообщений

    Returns:
        Настроенный объект логгера
    """
    global _logger_instance

    logger_obj = logging.getLogger('antispam')

    # Если логгер уже настроен, возвращаем его
    if logger_obj.handlers:
        return logger_obj

    # Создаем директорию для логов
    logs_path = Path(logs_dir)
    logs_path.mkdir(parents=True, exist_ok=True)

    # Формируем имя файла лога
    current_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    log_file = logs_path / f"{current_time}.log"

    logger_obj.setLevel(log_level)

    # Форматтер
    formatter = logging.Formatter(log_format)

    # Обработчик для файла
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger_obj.addHandler(file_handler)

    # Обработчик для консоли
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # Пробуем настроить кодировку для консоли
    try:
        if hasattr(console_handler.stream, 'reconfigure'):
            console_handler.stream.reconfigure(encoding='utf-8')
    except (AttributeError, OSError):
        pass

    logger_obj.addHandler(console_handler)

    # Выводим ASCII-art если есть
    ascii_art_path = Path('.info/ascii-art.txt')
    if ascii_art_path.exists():
        try:
            with open(ascii_art_path, 'r', encoding='utf-8') as f:
                print(f.read())
        except Exception:
            pass

    logger_obj.info(f"Логгер настроен. Файл логов: {log_file}")

    _logger_instance = logger_obj
    return logger_obj


def get_logger() -> logging.Logger:
    """
    Возвращает текущий экземпляр логгера.

    Returns:
        Объект логгера
    """
    global _logger_instance
    if _logger_instance is None:
        # Пытаемся загрузить конфиг для определения директории логов
        try:
            from utils.config import LOGS_DIR
            logs_dir = LOGS_DIR
        except Exception:
            logs_dir = 'logs'
        _logger_instance = setup_logger(logs_dir=logs_dir)
    return _logger_instance


# Создаем логгер при импорте
try:
    from utils.config import LOGS_DIR
    _logs_dir = LOGS_DIR
except Exception:
    _logs_dir = 'logs'

logger = setup_logger(logs_dir=_logs_dir)
