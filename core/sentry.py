"""Инициализация Sentry SDK для мониторинга ошибок и производительности.

Модуль предоставляет функцию init_sentry, которую следует вызивать
как можно раньше при запуске приложения.
"""

import logging

from core.config import (
    SENTRY_DSN,
    SENTRY_TRACES_SAMPLE_RATE,
    SENTRY_ENABLE_LOGS,
    SENTRY_LOGS_LEVEL,
    SENTRY_BREADCRUMBS_LEVEL,
    SENTRY_EVENT_LEVEL,
    APP_VERSION,
    TESTING,
)
from core.logging import logger

_initialized = False


def init_sentry() -> bool:
    """Инициализирует Sentry SDK, если задан SENTRY_DSN.

    Возвращаемое значение:
        success (bool): True, если Sentry инициализирован; False, если DSN не задан.
    """
    global _initialized

    if _initialized:
        return True

    if not SENTRY_DSN:
        logger.info("SENTRY_DSN не задан — мониторинг Sentry отключён.")
        return False

    import sentry_sdk
    from sentry_sdk.integrations.asyncio import AsyncioIntegration
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    _LEVEL_MAP = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL,
    }

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment='testing' if TESTING else 'production',
        release=APP_VERSION,
        traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
        enable_logs=SENTRY_ENABLE_LOGS,
        integrations=[
            LoggingIntegration(
                sentry_logs_level=_LEVEL_MAP.get(SENTRY_LOGS_LEVEL, logging.INFO),
                level=_LEVEL_MAP.get(SENTRY_BREADCRUMBS_LEVEL, logging.INFO),
                event_level=_LEVEL_MAP.get(SENTRY_EVENT_LEVEL, logging.ERROR),
            ),
            StarletteIntegration(),
            FastApiIntegration(),
            AsyncioIntegration(),
        ],
    )

    _initialized = True
    logger.info("Sentry инициализирован.")
    return True


def capture_exception(exc: Exception) -> None:
    """Отправляет исключение в Sentry, если он инициализирован.

    Аргументы:
        exc (Exception): Перехваченное исключение.
    """
    if not _initialized:
        return

    import sentry_sdk

    sentry_sdk.capture_exception(exc)


def capture_message(message: str, level: str = 'info') -> None:
    """Отправляет сообщение в Sentry, если он инициализирован.

    Аргументы:
        message (str): Текст сообщения.
        level (str): Уровень важности (info, warning, error).
    """
    if not _initialized:
        return

    import sentry_sdk

    sentry_sdk.capture_message(message, level=level)
