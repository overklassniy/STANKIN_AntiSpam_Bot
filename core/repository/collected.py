"""Репозиторий для работы с собранными сообщениями."""

from datetime import datetime
from typing import Optional

from core.db import get_pool


class CollectedRepository:
    """Репозиторий для собранных сообщений."""

    @staticmethod
    async def add_collected_message(
        chat_id: int,
        user_id: int,
        username: Optional[str],
        message_text: str
    ) -> None:
        """Добавляет собранное сообщение.

        Аргументы:
            chat_id (int): Telegram ID чата.
            user_id (int): Telegram ID пользователя.
            username (Optional[str]): Username.
            message_text (str): Текст сообщения.
        """
        pool = get_pool()
        timestamp = datetime.now().timestamp()
        await pool.execute(
            '''INSERT INTO collected_message (chat_id, user_id, username, message_text, timestamp)
               VALUES ($1, $2, $3, $4, $5)''',
            chat_id, user_id, username, message_text, timestamp
        )

    @staticmethod
    async def get_collected_count(chat_pk: Optional[int] = None) -> int:
        """Возвращает количество собранных сообщений.

        Аргументы:
            chat_pk (Optional[int]): PK чата для фильтрации.

        Возвращаемое значение:
            int: Количество записей.
        """
        pool = get_pool()
        if chat_pk is not None:
            return await pool.fetchval(
                'SELECT COUNT(*) FROM collected_message WHERE chat_id = $1', chat_pk
            )
        return await pool.fetchval('SELECT COUNT(*) FROM collected_message')

    @staticmethod
    async def get_collected_messages(
        chat_pk: Optional[int] = None,
        page: int = 1,
        per_page: int = 10
    ) -> dict:
        """Получает список собранных сообщений с пагинацией.

        Аргументы:
            chat_pk (Optional[int]): PK чата для фильтрации.
            page (int): Номер страницы.
            per_page (int): Записей на странице.

        Возвращаемое значение:
            dict: items, total, total_pages, current_page.
        """
        pool = get_pool()
        offset = (page - 1) * per_page

        if chat_pk is not None:
            total = await pool.fetchval(
                'SELECT COUNT(*) FROM collected_message WHERE chat_id = $1', chat_pk
            )
            rows = await pool.fetch(
                '''SELECT * FROM collected_message WHERE chat_id = $1
                   ORDER BY timestamp DESC LIMIT $2 OFFSET $3''',
                chat_pk, per_page, offset
            )
        else:
            total = await pool.fetchval('SELECT COUNT(*) FROM collected_message')
            rows = await pool.fetch(
                '''SELECT * FROM collected_message
                   ORDER BY timestamp DESC LIMIT $1 OFFSET $2''',
                per_page, offset
            )

        return {
            'items': [dict(row) for row in rows],
            'total': total,
            'total_pages': (total + per_page - 1) // per_page if per_page > 0 else 0,
            'current_page': page,
        }
