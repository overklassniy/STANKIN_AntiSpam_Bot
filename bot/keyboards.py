"""
Модуль для создания клавиатур бота.
"""

from typing import List, Optional

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def create_spam_notification_keyboard(
    message_id: int,
    user_id: int,
    include_delete: bool = True,
    include_mute: bool = True,
    include_not_spam: bool = True
) -> Optional[InlineKeyboardMarkup]:
    """
    Создает клавиатуру для уведомления о спаме.

    Args:
        message_id: ID сообщения в чате
        user_id: ID пользователя
        include_delete: Включить кнопку удаления
        include_mute: Включить кнопку ограничения
        include_not_spam: Включить кнопку "Не спам"

    Returns:
        InlineKeyboardMarkup или None, если нет кнопок
    """
    buttons: List[List[InlineKeyboardButton]] = []

    if include_delete:
        buttons.append([
            InlineKeyboardButton(
                text="🗑 Удалить сообщение",
                callback_data=f"delete_message:{message_id}"
            )
        ])

    if include_mute:
        buttons.append([
            InlineKeyboardButton(
                text="🔨 Ограничить пользователя",
                callback_data=f"mute_user:{user_id}"
            )
        ])

    if include_not_spam:
        buttons.append([
            InlineKeyboardButton(
                text="✅ Не спам",
                callback_data=f"not_spam:{user_id}"
            )
        ])

    return InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None


def create_unmute_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с кнопкой снятия ограничения.

    Args:
        user_id: ID пользователя

    Returns:
        InlineKeyboardMarkup
    """
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🔓 Снять ограничение",
            callback_data=f"unmute_user:{user_id}"
        )
    ]])


def remove_button_from_keyboard(
    keyboard: InlineKeyboardMarkup,
    callback_prefix: str
) -> Optional[InlineKeyboardMarkup]:
    """
    Удаляет кнопку с указанным префиксом из клавиатуры.

    Args:
        keyboard: Исходная клавиатура
        callback_prefix: Префикс callback_data для удаления

    Returns:
        Новая клавиатура без указанной кнопки или None
    """
    new_buttons = []
    for row in keyboard.inline_keyboard:
        new_row = [btn for btn in row if not btn.callback_data.startswith(callback_prefix)]
        if new_row:
            new_buttons.append(new_row)

    return InlineKeyboardMarkup(inline_keyboard=new_buttons) if new_buttons else None
