"""Модуль настройки логирования."""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'

_logger_instance: Optional[logging.Logger] = None


def setup_logger(
    logs_dir: str = 'logs',
    log_level: int = logging.INFO,
    log_format: str = LOG_FORMAT
) -> logging.Logger:
    """Настраивает и возвращает логгер.

    Аргументы:
        logs_dir (str): Директория для файлов логов.
        log_level (int): Уровень логирования.
        log_format (str): Формат сообщений.

    Возвращаемое значение:
        logging.Logger: Настроенный объект логгера.
    """
    global _logger_instance

    logger_obj = logging.getLogger('antispam')

    if logger_obj.handlers:
        return logger_obj

    logs_path = Path(logs_dir)
    logs_path.mkdir(parents=True, exist_ok=True)

    current_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    log_file = logs_path / f"{current_time}.log"

    logger_obj.setLevel(log_level)

    formatter = logging.Formatter(log_format)

    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger_obj.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    try:
        if hasattr(console_handler.stream, 'reconfigure'):
            console_handler.stream.reconfigure(encoding='utf-8')
    except (AttributeError, OSError):
        pass

    logger_obj.addHandler(console_handler)

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
    """Возвращает текущий экземпляр логгера.

    Если логгер ещё не создан, инициализирует его с директорией из конфигурации.

    Возвращаемое значение:
        logger (logging.Logger): Объект логгера.
    """
    global _logger_instance
    if _logger_instance is None:
        try:
            from core.config import LOGS_DIR
            logs_dir = LOGS_DIR
        except Exception:
            logs_dir = 'logs'
        _logger_instance = setup_logger(logs_dir=logs_dir)
    return _logger_instance


def get_uvicorn_log_config() -> dict:
    """Возвращает конфигурацию логирования для uvicorn в едином формате.

    Возвращаемое значение:
        config (dict): Словарь конфигурации в формате logging.config.dictConfig.
    """
    log_file = None
    if _logger_instance is not None:
        for handler in _logger_instance.handlers:
            if isinstance(handler, logging.FileHandler):
                log_file = handler.baseFilename
                break

    handlers = {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',
            'stream': 'ext://sys.stdout',
        },
    }
    handler_list = ['console']

    if log_file:
        handlers['file'] = {
            'class': 'logging.FileHandler',
            'formatter': 'default',
            'filename': log_file,
            'encoding': 'utf-8',
        }
        handler_list.append('file')

    return {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'default': {
                '()': 'logging.Formatter',
                'fmt': LOG_FORMAT,
            },
        },
        'handlers': handlers,
        'loggers': {
            'uvicorn': {
                'handlers': handler_list,
                'level': 'INFO',
                'propagate': False,
            },
            'uvicorn.error': {
                'handlers': handler_list,
                'level': 'INFO',
                'propagate': False,
            },
            'uvicorn.access': {
                'handlers': handler_list,
                'level': 'INFO',
                'propagate': False,
            },
        },
    }


def configure_third_party_loggers() -> None:
    """Настраивает логгеры сторонних библиотек в едином формате."""
    app_logger = get_logger()

    for name in ('aiogram', 'asyncpg', 'aiohttp', 'aiohttp_socks'):
        lib_logger = logging.getLogger(name)
        lib_logger.handlers.clear()
        for handler in app_logger.handlers:
            lib_logger.addHandler(handler)
        lib_logger.setLevel(app_logger.level)
        lib_logger.propagate = False


# Создаем логгер при импорте
try:
    from core.config import LOGS_DIR
    _logs_dir = LOGS_DIR
except Exception:
    _logs_dir = 'logs'

logger = setup_logger(logs_dir=_logs_dir)

configure_third_party_loggers()
