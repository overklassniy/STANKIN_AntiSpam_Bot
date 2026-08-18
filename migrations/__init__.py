"""Система миграций схемы БД на чистом asyncpg.

Миграции — нумерованные модули migrations/m*.py. Каждый экспортирует
MIGRATION_ID и async def upgrade(conn). Применяются автоматически при старте
приложения через migrations.runner.run_migrations.
"""
