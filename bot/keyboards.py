"""Модуль для создания клавиатур бота."""

from typing import List, Optional

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def create_spam_notification_keyboard(
    message_id: int,
    user_id: int,
    chat_id: int,
    include_delete: bool = True,
    include_mute: bool = True,
    include_not_spam: bool = True
) -> Optional[InlineKeyboardMarkup]:
    """Создает клавиатуру для уведомления о спаме.

    Аргументы:
        message_id (int): ID сообщения в чате.
        user_id (int): ID пользователя.
        chat_id (int): ID чата, где обнаружен спам.
        include_delete (bool): Включить кнопку удаления.
        include_mute (bool): Включить кнопку ограничения.
        include_not_spam (bool): Включить кнопку "Не спам".

    Возвращаемое значение:
        Optional[InlineKeyboardMarkup]: Клавиатура или None.
    """
    buttons: List[List[InlineKeyboardButton]] = []

    if include_delete:
        buttons.append([
            InlineKeyboardButton(
                text="Удалить сообщение",
                callback_data=f"delete_message:{chat_id}:{message_id}"
            )
        ])

    if include_mute:
        buttons.append([
            InlineKeyboardButton(
                text="Ограничить пользователя",
                callback_data=f"mute_user:{chat_id}:{user_id}"
            )
        ])

    if include_not_spam:
        buttons.append([
            InlineKeyboardButton(
                text="Не спам",
                callback_data=f"not_spam:{chat_id}:{user_id}"
            )
        ])

    return InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None


def create_unmute_keyboard(user_id: int, chat_id: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру с кнопкой снятия ограничения.

    Аргументы:
        user_id (int): ID пользователя.
        chat_id (int): ID чата.

    Возвращаемое значение:
        InlineKeyboardMarkup: Клавиатура.
    """
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="Снять ограничение",
            callback_data=f"unmute_user:{chat_id}:{user_id}"
        )
    ]])


def remove_button_from_keyboard(
    keyboard: InlineKeyboardMarkup,
    callback_prefix: str
) -> Optional[InlineKeyboardMarkup]:
    """Удаляет кнопку с указанным префиксом из клавиатуры.

    Аргументы:
        keyboard (InlineKeyboardMarkup): Исходная клавиатура.
        callback_prefix (str): Префикс callback_data для удаления.

    Возвращаемое значение:
        Optional[InlineKeyboardMarkup]: Новая клавиатура без указанной кнопки или None.
    """
    new_buttons = []
    for row in keyboard.inline_keyboard:
        new_row = [btn for btn in row if not btn.callback_data.startswith(callback_prefix)]
        if new_row:
            new_buttons.append(new_row)

    return InlineKeyboardMarkup(inline_keyboard=new_buttons) if new_buttons else None
