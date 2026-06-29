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
