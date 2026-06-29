"""Репозиторий для работы с ограниченными пользователями."""

from datetime import datetime
from typing import List, Optional

from core.db import get_pool


class MutedRepository:
    """Репозиторий для ограниченных пользователей."""

    @staticmethod
    async def get_muted_user(chat_pk: int, user_id: int) -> Optional[dict]:
        """Получает информацию об ограниченном пользователе.

        Аргументы:
            chat_pk (int): PK чата.
            user_id (int): Telegram ID пользователя.

        Возвращаемое значение:
            Optional[dict]: Запись или None.
        """
        pool = get_pool()
        row = await pool.fetchrow(
            'SELECT * FROM muted_user WHERE chat_id = $1 AND user_id = $2',
            chat_pk, user_id
        )
        return dict(row) if row else None

    @staticmethod
    async def create_muted_user(
        chat_pk: int,
        user_id: int,
        username: Optional[str],
        timestamp: float,
        muted_till_timestamp: Optional[float] = None,
        relapse_number: int = 1
    ) -> int:
        """Создаёт запись об ограниченном пользователе.

        Аргументы:
            chat_pk (int): PK чата.
            user_id (int): Telegram ID пользователя.
            username (Optional[str]): Username.
            timestamp (float): Unix timestamp.
            muted_till_timestamp (Optional[float]): До какого времени ограничен.
            relapse_number (int): Номер нарушения.

        Возвращаемое значение:
            int: ID созданной записи.
        """
        pool = get_pool()
        return await pool.fetchval(
            '''INSERT INTO muted_user
               (chat_id, user_id, username, timestamp, muted_till_timestamp, relapse_number)
               VALUES ($1, $2, $3, $4, $5, $6)
               RETURNING id''',
            chat_pk, user_id, username, timestamp, muted_till_timestamp, relapse_number
        )

    @staticmethod
    async def update_muted_user(
        chat_pk: int,
        user_id: int,
        timestamp: float,
        muted_till_timestamp: Optional[float],
        relapse_number: int
    ) -> None:
        """Обновляет запись об ограниченном пользователе.

        Аргументы:
            chat_pk (int): PK чата.
            user_id (int): Telegram ID пользователя.
            timestamp (float): Unix timestamp.
            muted_till_timestamp (Optional[float]): До какого времени ограничен.
            relapse_number (int): Номер нарушения.
        """
        pool = get_pool()
        await pool.execute(
            '''UPDATE muted_user SET timestamp = $1, muted_till_timestamp = $2, relapse_number = $3
               WHERE chat_id = $4 AND user_id = $5''',
            timestamp, muted_till_timestamp, relapse_number, chat_pk, user_id
        )

    @staticmethod
    async def clear_muted_till(chat_pk: int, user_id: int) -> None:
        """Очищает время ограничения пользователя.

        Аргументы:
            chat_pk (int): PK чата.
            user_id (int): Telegram ID пользователя.
        """
        pool = get_pool()
        await pool.execute(
            'UPDATE muted_user SET muted_till_timestamp = NULL WHERE chat_id = $1 AND user_id = $2',
            chat_pk, user_id
        )

    @staticmethod
    async def get_muted_users(
        chat_pks: Optional[List[int]] = None,
        page: int = 1,
        per_page: int = 10
    ) -> dict:
        """Получает список ограниченных с пагинацией.

        Аргументы:
            chat_pks (Optional[List[int]]): Список PK чатов для фильтрации (None = все).
            page (int): Номер страницы.
            per_page (int): Записей на странице.

        Возвращаемое значение:
            dict: items, total, total_pages, current_page.
        """
        pool = get_pool()
        offset = (page - 1) * per_page

        if chat_pks is not None:
            total = await pool.fetchval(
                'SELECT COUNT(*) FROM muted_user WHERE chat_id = ANY($1)', chat_pks
            )
            rows = await pool.fetch(
                '''SELECT * FROM muted_user WHERE chat_id = ANY($1)
                   ORDER BY timestamp DESC LIMIT $2 OFFSET $3''',
                chat_pks, per_page, offset
            )
        else:
            total = await pool.fetchval('SELECT COUNT(*) FROM muted_user')
            rows = await pool.fetch(
                '''SELECT * FROM muted_user
                   ORDER BY timestamp DESC LIMIT $1 OFFSET $2''',
                per_page, offset
            )

        return {
            'items': [dict(row) for row in rows],
            'total': total,
            'total_pages': (total + per_page - 1) // per_page if per_page > 0 else 0,
            'current_page': page,
        }
