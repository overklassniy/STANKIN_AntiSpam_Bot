"""Репозиторий для работы с белым списком."""

from datetime import datetime
from typing import Optional

from core.db import get_pool


class WhitelistRepository:
    """Репозиторий для белого списка."""

    @staticmethod
    async def is_whitelisted(chat_pk: int, user_id: int) -> bool:
        """Проверяет, находится ли пользователь в белом списке чата.

        Аргументы:
            chat_pk (int): PK чата.
            user_id (int): Telegram ID пользователя.

        Возвращаемое значение:
            bool: True если в белом списке.
        """
        pool = get_pool()
        result = await pool.fetchval(
            'SELECT 1 FROM whitelist_user WHERE chat_id = $1 AND user_id = $2',
            chat_pk, user_id
        )
        return result is not None

    @staticmethod
    async def add_to_whitelist(
        chat_pk: int,
        user_id: int,
        username: Optional[str] = None,
        added_by: Optional[int] = None,
        reason: Optional[str] = None
    ) -> None:
        """Добавляет пользователя в белый список чата.

        Аргументы:
            chat_pk (int): PK чата.
            user_id (int): Telegram ID пользователя.
            username (Optional[str]): Username.
            added_by (Optional[int]): Telegram ID добавившего.
            reason (Optional[str]): Причина добавления.
        """
        pool = get_pool()
        timestamp = datetime.now().timestamp()
        await pool.execute(
            '''INSERT INTO whitelist_user (chat_id, user_id, username, added_at, added_by, reason)
               VALUES ($1, $2, $3, $4, $5, $6)
               ON CONFLICT (chat_id, user_id) DO NOTHING''',
            chat_pk, user_id, username, timestamp, added_by, reason
        )

    @staticmethod
    async def remove_from_whitelist(chat_pk: int, user_id: int) -> None:
        """Удаляет пользователя из белого списка чата.

        Аргументы:
            chat_pk (int): PK чата.
            user_id (int): Telegram ID пользователя.
        """
        pool = get_pool()
        await pool.execute(
            'DELETE FROM whitelist_user WHERE chat_id = $1 AND user_id = $2',
            chat_pk, user_id
        )
