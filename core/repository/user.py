"""Репозиторий для работы с пользователями панели."""

from typing import List, Optional

from core.db import get_pool


class UserRepository:
    """Репозиторий для пользователей панели управления."""

    @staticmethod
    async def get_user_by_telegram_id(telegram_id: int) -> Optional[dict]:
        """Получает пользователя по Telegram ID.

        Аргументы:
            telegram_id (int): Telegram ID пользователя.

        Возвращаемое значение:
            Optional[dict]: Запись пользователя или None.
        """
        pool = get_pool()
        row = await pool.fetchrow(
            'SELECT * FROM app_user WHERE telegram_id = $1', telegram_id
        )
        return dict(row) if row else None

    @staticmethod
    async def get_user_by_name(name: str) -> Optional[dict]:
        """Получает пользователя по имени.

        Аргументы:
            name (str): Имя пользователя.

        Возвращаемое значение:
            Optional[dict]: Запись пользователя или None.
        """
        pool = get_pool()
        row = await pool.fetchrow(
            'SELECT * FROM app_user WHERE name = $1', name
        )
        return dict(row) if row else None

    @staticmethod
    async def get_user_by_id(user_id: int) -> Optional[dict]:
        """Получает пользователя по PK.

        Аргументы:
            user_id (int): PK пользователя.

        Возвращаемое значение:
            Optional[dict]: Запись пользователя или None.
        """
        pool = get_pool()
        row = await pool.fetchrow(
            'SELECT * FROM app_user WHERE id = $1', user_id
        )
        return dict(row) if row else None

    @staticmethod
    async def create_or_update_user(
        telegram_id: int,
        name: str,
        password_hash: str,
        is_superadmin: bool = False
    ) -> int:
        """Создаёт или обновляет пользователя панели.

        Аргументы:
            telegram_id (int): Telegram ID.
            name (str): Имя пользователя.
            password_hash (str): Хеш пароля.
            is_superadmin (bool): Является ли суперпользователем.

        Возвращаемое значение:
            int: PK пользователя.
        """
        pool = get_pool()
        existing = await pool.fetchval(
            'SELECT id FROM app_user WHERE telegram_id = $1', telegram_id
        )
        if existing:
            await pool.execute(
                '''UPDATE app_user SET name = $1, password_hash = $2, is_superadmin = $3
                   WHERE id = $4''',
                name, password_hash, is_superadmin, existing
            )
            return existing

        return await pool.fetchval(
            '''INSERT INTO app_user (telegram_id, name, password_hash, is_superadmin)
               VALUES ($1, $2, $3, $4) RETURNING id''',
            telegram_id, name, password_hash, is_superadmin
        )

    @staticmethod
    async def grant_chat_access(user_pk: int, chat_pk: int) -> None:
        """Даёт пользователю доступ к чату.

        Аргументы:
            user_pk (int): PK пользователя.
            chat_pk (int): PK чата.
        """
        pool = get_pool()
        await pool.execute(
            '''INSERT INTO user_chat_access (user_id, chat_id) VALUES ($1, $2)
               ON CONFLICT DO NOTHING''',
            user_pk, chat_pk
        )

    @staticmethod
    async def get_user_chats(user_pk: int) -> List[dict]:
        """Возвращает список чатов, к которым у пользователя есть доступ.

        Аргументы:
            user_pk (int): PK пользователя.

        Возвращаемое значение:
            List[dict]: Список чатов.
        """
        pool = get_pool()
        rows = await pool.fetch(
            '''SELECT c.id, c.chat_id, c.title, c.is_active
               FROM user_chat_access uca
               JOIN chat c ON uca.chat_id = c.id
               WHERE uca.user_id = $1 AND c.is_active = TRUE''',
            user_pk
        )
        return [dict(row) for row in rows]

    @staticmethod
    async def get_accessible_chat_pks(user_pk: int) -> List[int]:
        """Возвращает список PK чатов, доступных пользователю.

        Аргументы:
            user_pk (int): PK пользователя.

        Возвращаемое значение:
            List[int]: Список PK чатов.
        """
        pool = get_pool()
        rows = await pool.fetch(
            '''SELECT c.id FROM user_chat_access uca
               JOIN chat c ON uca.chat_id = c.id
               WHERE uca.user_id = $1 AND c.is_active = TRUE''',
            user_pk
        )
        return [row['id'] for row in rows]

    @staticmethod
    async def get_users_by_chat_pk(chat_pk: int) -> List[dict]:
        """Возвращает список пользователей, имеющих доступ к чату.

        Аргументы:
            chat_pk (int): PK чата.

        Возвращаемое значение:
            List[dict]: Список пользователей с полями id, name, telegram_id, is_superadmin.
        """
        pool = get_pool()
        rows = await pool.fetch(
            '''SELECT u.id, u.name, u.telegram_id, u.is_superadmin
               FROM user_chat_access uca
               JOIN app_user u ON uca.user_id = u.id
               WHERE uca.chat_id = $1
               ORDER BY u.name''',
            chat_pk
        )
        return [dict(row) for row in rows]

    @staticmethod
    async def is_superadmin(user_pk: int) -> bool:
        """Проверяет, является ли пользователь суперпользователем.

        Аргументы:
            user_pk (int): PK пользователя.

        Возвращаемое значение:
            bool: True если суперпользователь.
        """
        pool = get_pool()
        result = await pool.fetchval(
            'SELECT is_superadmin FROM app_user WHERE id = $1', user_pk
        )
        return bool(result) if result is not None else False
