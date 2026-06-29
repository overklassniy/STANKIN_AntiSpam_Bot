"""Управление asyncpg connection pool.

Единый пул соединений, используемый ботом и панелью.
"""

from typing import Optional

import asyncpg

from core.logging import logger

_pool: Optional[asyncpg.Pool] = None


async def init_pool(
    dsn: str,
    min_size: int = 2,
    max_size: int = 10
) -> asyncpg.Pool:
    """Создаёт и возвращает пул соединений PostgreSQL.

    Аргументы:
        dsn (str): Строка подключения к PostgreSQL.
        min_size (int): Минимальное количество соединений в пуле.
        max_size (int): Максимальное количество соединений в пуле.

    Возвращаемое значение:
        asyncpg.Pool: Пул соединений.

    Исключения:
        Exception: Если не удалось подключиться к базе данных.
    """
    global _pool
    logger.info(f"Инициализация пула соединений PostgreSQL: {dsn.split('@')[-1]}")
    _pool = await asyncpg.create_pool(
        dsn=dsn,
        min_size=min_size,
        max_size=max_size,
        command_timeout=30
    )
    logger.info("Пул соединений PostgreSQL создан.")
    return _pool


async def close_pool() -> None:
    """Закрывает пул соединений.

    Если пул не инициализирован, ничего не делает.
    """
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Пул соединений PostgreSQL закрыт.")


def get_pool() -> asyncpg.Pool:
    """Возвращает текущий пул соединений.

    Возвращаемое значение:
        asyncpg.Pool: Пул соединений.

    Исключения:
        RuntimeError: Если пул не инициализирован.
    """
    if _pool is None:
        raise RuntimeError("Пул соединений не инициализирован. Вызовите init_pool() сначала.")
    return _pool
