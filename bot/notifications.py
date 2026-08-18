"""Модуль для форматирования уведомлений.

Отправка уведомлений выполняется через NotificationService в bot.services.notifications.
"""

from datetime import datetime
from typing import Optional


def format_spam_notification(
    timestamp: float,
    author_id: int,
    author_name: Optional[str],
    message_text: str,
    has_reply_markup: Optional[bool],
    bert_score: float,
    relapse_number: int,
    auto_deleted: bool = False,
    muted_until: Optional[str] = None,
    chat_title: Optional[str] = None,
    chat_id: Optional[int] = None
) -> str:
    """Форматирует текст уведомления о спаме.

    Аргументы:
        timestamp (float): Unix timestamp.
        author_id (int): Telegram ID автора.
        author_name (Optional[str]): Username автора.
        message_text (str): Текст сообщения.
        has_reply_markup (Optional[bool]): Наличие inline-клавиатуры.
        bert_score (float): Оценка BERT.
        relapse_number (int): Номер нарушения.
        auto_deleted (bool): Удалено ли автоматически.
        muted_until (Optional[str]): До какого времени ограничен.
        chat_title (Optional[str]): Название чата.
        chat_id (Optional[int]): ID чата.

    Возвращаемое значение:
        str: HTML-форматированный текст уведомления.
    """
    ts_str = datetime.fromtimestamp(timestamp).strftime("%d.%m.%Y %H:%M:%S")

    if has_reply_markup is None:
        kb_status = 'Отключено'
    else:
        kb_status = 'Да' if has_reply_markup else 'Нет'

    text = (
        f"<b>Дата:</b> {ts_str}\n"
        f"<b>ID пользователя:</b> <code>{author_id}</code>\n"
        f"<b>Имя пользователя:</b> <code>{author_name}</code>\n"
    )

    if chat_title or chat_id:
        text += f"<b>Чат:</b> {chat_title or chat_id}\n"

    text += (
        f"<b>Текст сообщения:</b>\n<blockquote>{message_text}</blockquote>\n"
        f"<b>Имеет inline-клавиатуру:</b> {kb_status}\n"
        f"<b>Вердикт RuBert:</b> <code>{bert_score:.7f}</code>\n"
        f"<b>Количество нарушений:</b> {relapse_number}"
    )

    if auto_deleted:
        text += "\n<i>Сообщение удалено автоматически</i>"

    if muted_until:
        text += f"\n<b>Ограничен до:</b> {muted_until}"

    return text


def format_mute_notification(
    timestamp: float,
    user_id: int,
    username: Optional[str],
    muted_until: str,
    relapse_number: int
) -> str:
    """Форматирует текст уведомления об ограничении пользователя.

    Аргументы:
        timestamp (float): Unix timestamp.
        user_id (int): Telegram ID пользователя.
        username (Optional[str]): Username.
        muted_until (str): До какого времени ограничен.
        relapse_number (int): Номер нарушения.

    Возвращаемое значение:
        str: HTML-форматированный текст.
    """
    ts_str = datetime.fromtimestamp(timestamp).strftime("%d.%m.%Y %H:%M:%S")

    return (
        f"<b>Дата:</b> {ts_str}\n"
        f"<b>ID пользователя:</b> <code>{user_id}</code>\n"
        f"<b>Имя пользователя:</b> <code>{username}</code>\n"
        f"<b>Дата окончания ограничения:</b> {muted_until}\n"
        f"<b>Количество нарушений:</b> {relapse_number}"
    )


def format_whitelist_added_notification(
    timestamp: float,
    user_id: int,
    username: Optional[str],
    added_by: Optional[int],
    added_by_username: Optional[str],
    reason: Optional[str],
    chat_id: int,
    chat_title: Optional[str] = None
) -> str:
    """Форматирует текст уведомления о добавлении пользователя в белый список.

    Аргументы:
        timestamp (float): Unix timestamp добавления.
        user_id (int): Telegram ID пользователя.
        username (Optional[str]): Username добавленного пользователя.
        added_by (Optional[int]): Telegram ID пользователя, который добавил.
        added_by_username (Optional[str]): Username добавившего.
        reason (Optional[str]): Причина добавления.
        chat_id (int): ID чата, в котором добавлен пользователь.
        chat_title (Optional[str]): Название чата.

    Возвращаемое значение:
        str: HTML-форматированный текст уведомления.
    """
    ts_str = datetime.fromtimestamp(timestamp).strftime("%d.%m.%Y %H:%M:%S")

    text = (
        f"<b>Пользователь добавлен в белый список</b>\n"
        f"<b>Дата:</b> {ts_str}\n"
        f"<b>ID пользователя:</b> <code>{user_id}</code>\n"
        f"<b>Имя пользователя:</b> <code>{username or 'нет'}</code>\n"
    )

    if chat_title or chat_id:
        text += f"<b>Чат:</b> {chat_title or chat_id}\n"

    if added_by is not None:
        if added_by_username:
            text += f"<b>Добавил:</b> <code>{added_by}</code> (@{added_by_username})\n"
        else:
            text += f"<b>Добавил:</b> <code>{added_by}</code>\n"

    if reason:
        text += f"<b>Причина:</b> {reason}"

    return text


def format_log_notification(
    timestamp: float,
    author_id: int,
    author_name: Optional[str],
    message_text: str,
    has_reply_markup: Optional[bool],
    bert_score: Optional[float],
    relapse_number: Optional[int],
    is_whitelisted: bool = False,
    content_type: Optional[str] = None,
    chat_title: Optional[str] = None,
    chat_id: Optional[int] = None
) -> str:
    """Форматирует текст логируемого сообщения для отправки в топик.

    Аргументы:
        timestamp (float): Unix timestamp.
        author_id (int): Telegram ID автора.
        author_name (Optional[str]): Username автора.
        message_text (str): Текст сообщения или заглушка для нетекстовых.
        has_reply_markup (Optional[bool]): Наличие inline-клавиатуры.
        bert_score (Optional[float]): Оценка BERT или None если не запускался.
        relapse_number (Optional[int]): Номер нарушения или None.
        is_whitelisted (bool): В белом ли списке пользователь.
        content_type (Optional[str]): Тип контента для нетекстовых сообщений.
        chat_title (Optional[str]): Название чата.
        chat_id (Optional[int]): ID чата.

    Возвращаемое значение:
        str: HTML-форматированный текст.
    """
    ts_str = datetime.fromtimestamp(timestamp).strftime("%d.%m.%Y %H:%M:%S")

    if has_reply_markup is None:
        kb_status = 'Отключено'
    else:
        kb_status = 'Да' if has_reply_markup else 'Нет'

    text = (
        f"<b>Дата:</b> {ts_str}\n"
        f"<b>ID пользователя:</b> <code>{author_id}</code>\n"
        f"<b>Имя пользователя:</b> <code>{author_name}</code>\n"
    )

    if chat_title or chat_id:
        text += f"<b>Чат:</b> {chat_title or chat_id}\n"

    if content_type:
        text += f"<b>Тип контента:</b> {content_type}\n"
        text += f"<b>Текст сообщения:</b>\n<blockquote>{message_text}</blockquote>\n"
    else:
        text += f"<b>Текст сообщения:</b>\n<blockquote>{message_text}</blockquote>\n"

    text += f"<b>Имеет inline-клавиатуру:</b> {kb_status}\n"

    if is_whitelisted:
        text += "<b>Статус:</b> Вайтлистед\n"

    if bert_score is not None:
        text += f"<b>Вердикт RuBert:</b> <code>{bert_score:.7f}</code>\n"
    else:
        text += "<b>Вердикт RuBert:</b> N/A\n"

    text += f"<b>Количество нарушений:</b> {relapse_number if relapse_number is not None else 0}"

    return text
