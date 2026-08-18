"""Миграция m001: удаляет глобальные настройки логирования.

LOG_TO_TOPIC и LOG_TOPIC_ID — per-chat настройки (лог-топик настраивается
индивидуально для каждого чата). Глобальные записи в global_setting были
созданы ранее через init_default_global_settings и больше не нужны:
они не отображаются в панели и не должны использоваться как fallback.

После миграции fallback идёт через DEFAULT_SETTINGS (LOG_TO_TOPIC=False,
LOG_TOPIC_ID=0), а per-chat значения сохраняются.
"""

MIGRATION_ID = "m001_remove_global_log_settings"


async def upgrade(conn) -> None:
    """Удаляет глобальные записи LOG_TO_TOPIC и LOG_TOPIC_ID.

    Аргументы:
        conn (asyncpg.Connection): Соединение с БД внутри транзакции.
    """
    await conn.execute(
        "DELETE FROM global_setting WHERE key IN ('LOG_TO_TOPIC', 'LOG_TOPIC_ID')"
    )
