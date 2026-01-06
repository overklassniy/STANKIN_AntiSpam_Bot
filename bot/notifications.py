"""
Модуль для отправки уведомлений.
"""

import asyncio
from datetime import datetime
from typing import Optional

from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup

from bot.core import get_bot
from bot.keyboards import create_unmute_keyboard
from utils.config import NOTIFICATION_CHAT_ID, NOTIFICATION_CHAT_MUTED_THREAD
from utils.logging import logger


def format_spam_notification(
    timestamp: float,
    author_id: int,
    author_name: Optional[str],
    message_text: str,
    has_reply_markup: Optional[bool],
    bert_score: float,
    relapse_number: int,
    auto_deleted: bool = False,
    muted_until: Optional[str] = None
) -> str:
    """
    Форматирует текст уведомления о спаме.
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
    """
    Форматирует текст уведомления об ограничении пользователя.
    """
    ts_str = datetime.fromtimestamp(timestamp).strftime("%d.%m.%Y %H:%M:%S")

    return (
        f"<b>Дата:</b> {ts_str}\n"
        f"<b>ID пользователя:</b> <code>{user_id}</code>\n"
        f"<b>Имя пользователя:</b> <code>{username}</code>\n"
        f"<b>Дата окончания ограничения:</b> {muted_until}\n"
        f"<b>Количество нарушений:</b> {relapse_number}"
    )


async def send_spam_notification(
    thread_id: int,
    text: str,
    keyboard: Optional[InlineKeyboardMarkup] = None,
    max_retries: int = 3
) -> bool:
    """
    Отправляет уведомление о спаме в указанный тред с повторными попытками.

    Args:
        thread_id: ID треда для уведомления
        text: Текст уведомления
        keyboard: Клавиатура (опционально)
        max_retries: Максимальное количество попыток

    Returns:
        True если успешно отправлено, False в случае ошибки
    """
    bot = get_bot()
    
    for attempt in range(max_retries):
        try:
            await bot.send_message(
                chat_id=NOTIFICATION_CHAT_ID,
                message_thread_id=thread_id,
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
            logger.info("Уведомление о спаме отправлено")
            return True
            
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Экспоненциальная задержка: 1s, 2s, 4s
                logger.warning(
                    f"Ошибка отправки уведомления о спаме (попытка {attempt + 1}/{max_retries}): {e}. "
                    f"Повтор через {wait_time}с..."
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Не удалось отправить уведомление о спаме после {max_retries} попыток: {e}")
                return False
    
    return False


async def send_mute_notification(
    user_id: int,
    username: Optional[str],
    muted_until: str,
    relapse_number: int,
    max_retries: int = 3
) -> bool:
    """
    Отправляет уведомление об ограничении пользователя с повторными попытками.

    Args:
        user_id: ID пользователя
        username: Username пользователя
        muted_until: Дата окончания ограничения
        relapse_number: Номер нарушения
        max_retries: Максимальное количество попыток

    Returns:
        True если успешно отправлено, False в случае ошибки
    """
    bot = get_bot()
    timestamp = datetime.now().timestamp()

    text = format_mute_notification(
        timestamp=timestamp,
        user_id=user_id,
        username=username,
        muted_until=muted_until,
        relapse_number=relapse_number
    )

    keyboard = create_unmute_keyboard(user_id)

    for attempt in range(max_retries):
        try:
            await bot.send_message(
                chat_id=NOTIFICATION_CHAT_ID,
                message_thread_id=NOTIFICATION_CHAT_MUTED_THREAD,
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
            logger.info(f"Уведомление об ограничении пользователя {user_id} отправлено")
            return True
            
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Экспоненциальная задержка: 1s, 2s, 4s
                logger.warning(
                    f"Ошибка отправки уведомления об ограничении (попытка {attempt + 1}/{max_retries}): {e}. "
                    f"Повтор через {wait_time}с..."
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Не удалось отправить уведомление об ограничении после {max_retries} попыток: {e}")
                return False
    
    return False
