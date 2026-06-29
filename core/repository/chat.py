"""Репозиторий для работы с чатами."""

from typing import List, Optional

from core.db import get_pool


class ChatRepository:
    """Репозиторий для управления наблюдаемыми чатами."""

    @staticmethod
    async def add_chat(chat_id: int, title: Optional[str] = None) -> int:
        """Добавляет чат в наблюдаемые и возвращает его PK.

        Аргументы:
            chat_id (int): Telegram ID чата.
            title (Optional[str]): Название чата.

        Возвращаемое значение:
            int: PK записи в таблице chat.
        """
        pool = get_pool()
        existing = await pool.fetchval(
            'SELECT id FROM chat WHERE chat_id = $1', chat_id
        )
        if existing:
            await pool.execute(
                'UPDATE chat SET is_active = TRUE, title = $2 WHERE id = $1',
                existing, title
            )
            return existing

        return await pool.fetchval(
            '''INSERT INTO chat (chat_id, title, is_active) VALUES ($1, $2, TRUE)
               RETURNING id''',
            chat_id, title
        )

    @staticmethod
    async def deactivate_chat(chat_id: int) -> None:
        """Деактивирует чат (бот больше не админ).

        Аргументы:
            chat_id (int): Telegram ID чата.
        """
        pool = get_pool()
        await pool.execute(
            'UPDATE chat SET is_active = FALSE WHERE chat_id = $1', chat_id
        )

    @staticmethod
    async def get_active_chats() -> List[dict]:
        """Возвращает список всех активных чатов.

        Возвращаемое значение:
            List[dict]: Список чатов с полями id, chat_id, title.
        """
        pool = get_pool()
        rows = await pool.fetch(
            'SELECT id, chat_id, title FROM chat WHERE is_active = TRUE'
        )
        return [dict(row) for row in rows]

    @staticmethod
    async def get_chat_by_telegram_id(chat_id: int) -> Optional[dict]:
        """Получает чат по Telegram ID.

        Аргументы:
            chat_id (int): Telegram ID чата.

        Возвращаемое значение:
            Optional[dict]: Запись чата или None.
        """
        pool = get_pool()
        row = await pool.fetchrow(
            'SELECT id, chat_id, title, is_active FROM chat WHERE chat_id = $1', chat_id
        )
        return dict(row) if row else None

    @staticmethod
    async def get_chat_pk(chat_id: int) -> Optional[int]:
        """Получает PK чата по Telegram ID.

        Аргументы:
            chat_id (int): Telegram ID чата.

        Возвращаемое значение:
            Optional[int]: PK чата или None.
        """
        pool = get_pool()
        return await pool.fetchval(
            'SELECT id FROM chat WHERE chat_id = $1 AND is_active = TRUE', chat_id
        )

    @staticmethod
    async def is_observed(chat_id: int) -> bool:
        """Проверяет, является ли чат наблюдаемым и активным.

        Аргументы:
            chat_id (int): Telegram ID чата.

        Возвращаемое значение:
            bool: True если чат наблюдается.
        """
        pk = await ChatRepository.get_chat_pk(chat_id)
        return pk is not None
