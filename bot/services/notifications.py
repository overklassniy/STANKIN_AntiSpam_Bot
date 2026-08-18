"""Сервис уведомлений в чат управления.

Отправляет уведомления о спаме и ограничениях в NOTIFICATION_CHAT_ID
с inline-кнопками для ручных действий.
"""

from typing import Optional

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup

from core.config import (
    NOTIFICATION_CHAT_ID,
    NOTIFICATION_CHAT_98_SPAM_THREAD,
    NOTIFICATION_CHAT_94_SPAM_THREAD,
    NOTIFICATION_CHAT_NS_SPAM_THREAD,
    NOTIFICATION_CHAT_MUTED_THREAD,
    NOTIFICATION_CHAT_WHITELIST_THREAD,
)
from core.logging import logger


class NotificationService:
    """Сервис отправки уведомлений в чат управления."""

    @staticmethod
    def get_spam_thread(ausure: bool, not_sure: bool = False) -> int:
        """Определяет ID треда для спам-уведомления.

        Аргументы:
            ausure (bool): Высокая ли уверенность в спаме.
            not_sure (bool): Категория NOT SURE (email в сообщении).

        Возвращаемое значение:
            int: ID треда.
        """
        if not_sure:
            return NOTIFICATION_CHAT_NS_SPAM_THREAD
        if ausure:
            return NOTIFICATION_CHAT_98_SPAM_THREAD
        return NOTIFICATION_CHAT_94_SPAM_THREAD

    @staticmethod
    async def send_spam_notification(
        bot: Bot,
        text: str,
        keyboard: Optional[InlineKeyboardMarkup] = None,
        thread_id: Optional[int] = None
    ) -> bool:
        """Отправляет уведомление о спаме в чат управления.

        Аргументы:
            bot (Bot): Экземпляр бота.
            text (str): Текст уведомления.
            keyboard (Optional[InlineKeyboardMarkup]): Inline-клавиатура.
            thread_id (Optional[int]): ID треда.

        Возвращаемое значение:
            bool: True если отправлено успешно.
        """
        if not NOTIFICATION_CHAT_ID:
            logger.error("NOTIFICATION_CHAT_ID не задан")
            return False

        for attempt in range(3):
            try:
                await bot.send_message(
                    chat_id=NOTIFICATION_CHAT_ID,
                    text=text,
                    parse_mode='HTML',
                    reply_markup=keyboard,
                    message_thread_id=thread_id
                )
                return True
            except Exception as e:
                logger.warning(f"Попытка {attempt + 1} отправки уведомления не удалась: {e}")
                if attempt < 2:
                    import asyncio
                    await asyncio.sleep(1)

        logger.error("Не удалось отправить уведомление после 3 попыток")
        return False

    @staticmethod
    async def send_mute_notification(
        bot: Bot,
        user_id: int,
        username: Optional[str],
        muted_until: Optional[str],
        relapse: int,
        chat_id: Optional[int] = None
    ) -> bool:
        """Отправляет уведомление об ограничении пользователя.

        Аргументы:
            bot (Bot): Экземпляр бота.
            user_id (int): Telegram ID пользователя.
            username (Optional[str]): Username.
            muted_until (Optional[str]): До какого времени ограничен.
            relapse (int): Номер нарушения.
            chat_id (Optional[int]): ID чата, где ограничен пользователь.

        Возвращаемое значение:
            bool: True если отправлено успешно.
        """
        if not NOTIFICATION_CHAT_ID:
            return False

        from bot.keyboards import create_unmute_keyboard

        text = (
            f"<b>Пользователь ограничен</b>\n"
            f"ID: <code>{user_id}</code>\n"
            f"Username: @{username or 'нет'}\n"
            f"Нарушение: #{relapse}\n"
        )
        if muted_until:
            text += f"Ограничен до: {muted_until}\n"

        keyboard = create_unmute_keyboard(user_id, chat_id) if chat_id else None

        try:
            await bot.send_message(
                chat_id=NOTIFICATION_CHAT_ID,
                text=text,
                parse_mode='HTML',
                reply_markup=keyboard,
                message_thread_id=NOTIFICATION_CHAT_MUTED_THREAD
            )
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления об ограничении: {e}")
            return False

    @staticmethod
    async def send_whitelist_notification(
        bot: Bot,
        user_id: int,
        username: Optional[str],
        added_by: Optional[int],
        added_by_username: Optional[str],
        reason: Optional[str],
        chat_id: int,
        chat_title: Optional[str] = None
    ) -> bool:
        """Отправляет уведомление о добавлении пользователя в белый список в топик вайтлиста.

        Аргументы:
            bot (Bot): Экземпляр бота.
            user_id (int): Telegram ID добавленного пользователя.
            username (Optional[str]): Username добавленного пользователя.
            added_by (Optional[int]): Telegram ID пользователя, который добавил.
            added_by_username (Optional[str]): Username добавившего.
            reason (Optional[str]): Причина добавления.
            chat_id (int): ID чата, в котором добавлен пользователь.
            chat_title (Optional[str]): Название чата.

        Возвращаемое значение:
            bool: True если отправлено успешно.
        """
        if not NOTIFICATION_CHAT_ID:
            return False

        from datetime import datetime
        from bot.notifications import format_whitelist_added_notification
        from bot.keyboards import create_unwhitelist_keyboard

        text = format_whitelist_added_notification(
            timestamp=datetime.now().timestamp(),
            user_id=user_id,
            username=username,
            added_by=added_by,
            added_by_username=added_by_username,
            reason=reason,
            chat_id=chat_id,
            chat_title=chat_title,
        )
        keyboard = create_unwhitelist_keyboard(user_id, chat_id)

        try:
            await bot.send_message(
                chat_id=NOTIFICATION_CHAT_ID,
                text=text,
                parse_mode='HTML',
                reply_markup=keyboard,
                message_thread_id=NOTIFICATION_CHAT_WHITELIST_THREAD
            )
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки вайтлист-уведомления: {e}")
            return False
