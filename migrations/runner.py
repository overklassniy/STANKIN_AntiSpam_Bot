"""Лёгкий runner миграций на чистом asyncpg.

Применяет недостающие миграции из migrations/m*.py при старте приложения.
Без внешних зависимостей, использует существующий пул соединений.

Алгоритм:
    1. Взять advisory-блокировку, чтобы исключить гонку между процессами.
    2. Создать таблицу _migration, если её нет.
    3. Прочитать уже применённые MIGRATION_ID.
    4. Импортировать все модули migrations.m*, отсортировать по номеру.
    5. Применить недостающие в отдельной транзакции каждый.
"""

import importlib
import pkgutil
from typing import List, Tuple

import asyncpg

from core.logging import logger


# Постоянный ключ advisory-блокировки для runner миграций.
# Гарантирует, что только один процесс применяет миграции одновременно.
_MIGRATION_ADVISORY_KEY = 0x4D494752  # "MIGR" в hex


async def _ensure_migration_table(conn: asyncpg.Connection) -> None:
    """Создаёт таблицу _migration, если её нет.

    Аргументы:
        conn (asyncpg.Connection): Соединение с БД.
    """
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS _migration (
            id TEXT PRIMARY KEY,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )


async def _applied_ids(conn: asyncpg.Connection) -> List[str]:
    """Возвращает список уже применённых MIGRATION_ID.

    Аргументы:
        conn (asyncpg.Connection): Соединение с БД.

    Возвращаемое значение:
        List[str]: Применённые идентификаторы миграций.
    """
    rows = await conn.fetch('SELECT id FROM _migration')
    return [row['id'] for row in rows]


def _discover_migrations() -> List[Tuple[int, object]]:
    """Обнаруживает модули миграций и возвращает их с номерами.

    Возвращаемое значение:
        List[Tuple[int, object]]: Список (номер, модуль), отсортированный по номеру.
    """
    import migrations as migrations_pkg

    found: List[Tuple[int, object]] = []
    for module_info in pkgutil.iter_modules(migrations_pkg.__path__):
        name = module_info.name
        # Только модули вида mNNN_...
        if not name.startswith('m') or not name[1:4].isdigit():
            continue
        try:
            number = int(name[1:4])
        except ValueError:
            continue
        module = importlib.import_module(f'migrations.{name}')
        if not hasattr(module, 'MIGRATION_ID') or not hasattr(module, 'upgrade'):
            logger.warning(f"Модуль миграции {name} не экспортирует MIGRATION_ID/upgrade — пропущен")
            continue
        found.append((number, module))

    found.sort(key=lambda item: item[0])
    return found


async def run_migrations(pool: asyncpg.Pool) -> None:
    """Применяет все недостающие миграции.

    Использует advisory-блокировку, чтобы исключить конкурентный запуск
    нескольких процессов миграции против одной БД.

    Аргументы:
        pool (asyncpg.Pool): Пул соединений asyncpg.
    """
    async with pool.acquire() as conn:
        # Advisory-блокировка на время применения миграций.
        # pg_try_advisory_lock возвращает true, если блокировку удалось взять.
        got_lock = await conn.fetchval(
            'SELECT pg_try_advisory_lock($1)', _MIGRATION_ADVISORY_KEY
        )
        if not got_lock:
            logger.info("Миграции применяются другим процессом — пропускаем")
            return

        try:
            await _ensure_migration_table(conn)
            applied = set(await _applied_ids(conn))
            migrations = _discover_migrations()

            if not migrations:
                logger.info("Миграций не найдено")
                return

            pending = [(num, mod) for num, mod in migrations if mod.MIGRATION_ID not in applied]
            if not pending:
                logger.info(f"Все миграции уже применены (всего {len(migrations)})")
                return

            logger.info(f"Применяется миграций: {len(pending)} из {len(migrations)}")

            for number, module in pending:
                migration_id = module.MIGRATION_ID
                async with conn.transaction():
                    await module.upgrade(conn)
                    await conn.execute(
                        'INSERT INTO _migration (id) VALUES ($1) ON CONFLICT DO NOTHING',
                        migration_id,
                    )
                logger.info(f"Применена миграция {migration_id}")

            logger.info("Миграции успешно применены")
        finally:
            await conn.execute('SELECT pg_advisory_unlock($1)', _MIGRATION_ADVISORY_KEY)
