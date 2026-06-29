"""Репозиторий для работы со спам-сообщениями."""

from typing import List, Optional

from core.db import get_pool


class SpamRepository:
    """Репозиторий для спам-сообщений."""

    @staticmethod
    async def add_spam_message(
        chat_id: int,
        message_id: Optional[int],
        timestamp: float,
        author_id: int,
        author_username: Optional[str],
        message_text: str,
        has_reply_markup: Optional[bool] = None,
        cas: Optional[bool] = None,
        lols: Optional[bool] = None,
        chatgpt_prediction: Optional[float] = None,
        bert_prediction: Optional[float] = None
    ) -> int:
        """Добавляет запись о спам-сообщении.

        Аргументы:
            chat_id (int): Telegram ID чата.
            message_id (Optional[int]): ID сообщения в Telegram.
            timestamp (float): Unix timestamp.
            author_id (int): Telegram ID автора.
            author_username (Optional[str]): Username автора.
            message_text (str): Текст сообщения.
            has_reply_markup (Optional[bool]): Наличие inline-клавиатуры.
            cas (Optional[bool]): Результат проверки CAS.
            lols (Optional[bool]): Результат проверки LOLS.
            chatgpt_prediction (Optional[float]): Результат ChatGPT.
            bert_prediction (Optional[float]): Результат BERT.

        Возвращаемое значение:
            int: ID созданной записи.
        """
        pool = get_pool()
        return await pool.fetchval(
            '''INSERT INTO spam_message
               (chat_id, message_id, timestamp, author_id, author_username,
                message_text, has_reply_markup, cas, lols, chatgpt_prediction, bert_prediction)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
               RETURNING id''',
            chat_id, message_id, timestamp, author_id, author_username,
            message_text, has_reply_markup, cas, lols,
            chatgpt_prediction, bert_prediction
        )

    @staticmethod
    async def get_spam_messages(
        chat_pks: Optional[List[int]] = None,
        page: int = 1,
        per_page: int = 10
    ) -> dict:
        """Получает список спам-сообщений с пагинацией.

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
                '''SELECT COUNT(*) FROM spam_message s
                   JOIN chat c ON s.chat_id = c.chat_id
                   WHERE c.id = ANY($1)''',
                chat_pks
            )
            rows = await pool.fetch(
                '''SELECT s.* FROM spam_message s
                   JOIN chat c ON s.chat_id = c.chat_id
                   WHERE c.id = ANY($1)
                   ORDER BY s.timestamp DESC LIMIT $2 OFFSET $3''',
                chat_pks, per_page, offset
            )
        else:
            total = await pool.fetchval('SELECT COUNT(*) FROM spam_message')
            rows = await pool.fetch(
                '''SELECT * FROM spam_message
                   ORDER BY timestamp DESC LIMIT $1 OFFSET $2''',
                per_page, offset
            )

        return {
            'items': [dict(row) for row in rows],
            'total': total,
            'total_pages': (total + per_page - 1) // per_page if per_page > 0 else 0,
            'current_page': page,
        }

    @staticmethod
    async def get_spam_count(chat_pk: Optional[int] = None) -> int:
        """Возвращает количество спам-сообщений.

        Аргументы:
            chat_pk (Optional[int]): PK чата для фильтрации.

        Возвращаемое значение:
            int: Количество записей.
        """
        pool = get_pool()
        if chat_pk is not None:
            return await pool.fetchval(
                'SELECT COUNT(*) FROM spam_message WHERE chat_id = $1', chat_pk
            )
        return await pool.fetchval('SELECT COUNT(*) FROM spam_message')
