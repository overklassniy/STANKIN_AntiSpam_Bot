"""Обработчики callback-запросов (нажатия на inline-кнопки).

Формат callback_data включает chat_id:
- delete_message:{chat_id}:{message_id}
- mute_user:{chat_id}:{user_id}
- mute_forever:{chat_id}:{user_id}
- unmute_user:{chat_id}:{user_id}
- not_spam:{chat_id}:{user_id}
- unwhitelist:{chat_id}:{user_id}
"""

import re
from datetime import datetime

from aiogram import types
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest

from bot.core import dp, get_bot
from bot.keyboards import remove_button_from_keyboard
from bot.services.notifications import NotificationService
from core.repository.chat import ChatRepository
from core.repository.muted import MutedRepository
from core.repository.whitelist import WhitelistRepository
from core.utils import add_hours_get_timestamp
from core.logging import logger


@dp.callback_query(lambda c: c.data.startswith("mute_user"))
async def process_mute_user_callback(callback: types.CallbackQuery) -> None:
    """Обрабатывает нажатие на кнопку «Ограничить пользователя».

    Аргументы:
        callback (CallbackQuery): Callback-запрос от inline-кнопки.
    """
    try:
        parts = callback.data.split(":")
        if len(parts) != 3:
            await callback.answer("Неверные данные!")
            return

        chat_id = int(parts[1])
        user_id = int(parts[2])
        bot = get_bot()

        chat_pk = await ChatRepository.get_chat_pk(chat_id)
        if chat_pk is None:
            await callback.answer("Чат не найден!")
            return

        muted_user = await MutedRepository.get_muted_user(chat_pk, user_id)
        if not muted_user:
            await callback.answer("Пользователь не найден в базе данных!")
            return

        relapse_number = muted_user['relapse_number']
        username = muted_user['username']

        if relapse_number == 1:
            until_timestamp = add_hours_get_timestamp(24)
        elif relapse_number == 2:
            until_timestamp = add_hours_get_timestamp(168)
        else:
            until_timestamp = add_hours_get_timestamp(999)

        await MutedRepository.update_muted_user(
            chat_pk, user_id,
            datetime.now().timestamp(),
            until_timestamp,
            relapse_number
        )

        mute_permissions = types.ChatPermissions(can_send_messages=False)
        await bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=mute_permissions,
            until_date=until_timestamp
        )

        until_str = datetime.fromtimestamp(until_timestamp).strftime("%d.%m.%Y %H:%M:%S")

        original_text = getattr(callback.message, "html_text", callback.message.text)
        new_text = original_text + f'\n<b>Ограничен до:</b> {until_str}'

        new_markup = remove_button_from_keyboard(callback.message.reply_markup, "mute_user")
        await callback.message.edit_text(new_text, parse_mode=ParseMode.HTML, reply_markup=new_markup)

        await callback.answer("Пользователь ограничен!")
        logger.info(f"Пользователь {user_id} ограничен до {until_str} (рецидив №{relapse_number})")

        await NotificationService.send_mute_notification(
            bot, user_id, username, until_str, relapse_number, chat_id
        )

    except Exception as e:
        logger.error(f"Ошибка в обработчике mute_user: {e}")
        await callback.answer("Ошибка при ограничении пользователя!")


@dp.callback_query(lambda c: c.data.startswith("mute_forever"))
async def process_mute_forever_callback(callback: types.CallbackQuery) -> None:
    """Обрабатывает нажатие на кнопку «Ограничить пользователя (навсегда)».

    Ограничивает пользователя до 2100 года и устанавливает relapse_number=999.

    Аргументы:
        callback (CallbackQuery): Callback-запрос от inline-кнопки.
    """
    try:
        parts = callback.data.split(":")
        if len(parts) != 3:
            await callback.answer("Неверные данные!")
            return

        chat_id = int(parts[1])
        user_id = int(parts[2])
        bot = get_bot()

        chat_pk = await ChatRepository.get_chat_pk(chat_id)
        if chat_pk is None:
            await callback.answer("Чат не найден!")
            return

        muted_user = await MutedRepository.get_muted_user(chat_pk, user_id)
        username = muted_user['username'] if muted_user else None

        # Проверяем, не ограничен ли уже навсегда
        if muted_user and muted_user.get('muted_till_timestamp') is not None:
            if muted_user['muted_till_timestamp'] >= 4102455600.0:
                await callback.answer("Уже ограничен навсегда!")
                return

        until_timestamp = 4102455600.0
        current_timestamp = datetime.now().timestamp()

        if muted_user:
            await MutedRepository.update_muted_user(
                chat_pk, user_id, current_timestamp, until_timestamp, 999
            )
        else:
            await MutedRepository.create_muted_user(
                chat_pk, user_id, username, current_timestamp, until_timestamp, 999
            )

        mute_permissions = types.ChatPermissions(can_send_messages=False)
        await bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=mute_permissions,
            until_date=until_timestamp
        )

        until_str = datetime.fromtimestamp(until_timestamp).strftime("%d.%m.%Y %H:%M:%S")

        original_text = getattr(callback.message, "html_text", callback.message.text)
        new_text = original_text + f'\n<b>Ограничен навсегда (до {until_str})</b>'

        # Удаляем кнопки mute_user и mute_forever из клавиатуры
        new_markup = remove_button_from_keyboard(callback.message.reply_markup, "mute_user")
        if new_markup:
            new_markup = remove_button_from_keyboard(new_markup, "mute_forever")
        await callback.message.edit_text(new_text, parse_mode=ParseMode.HTML, reply_markup=new_markup)

        await callback.answer("Пользователь ограничен навсегда!")
        logger.info(f"Пользователь {user_id} ограничен навсегда (relapse=999)")

        await NotificationService.send_mute_notification(
            bot, user_id, username, until_str, 999, chat_id
        )

    except Exception as e:
        logger.error(f"Ошибка в обработчике mute_forever: {e}")
        await callback.answer("Ошибка при ограничении пользователя!")


@dp.callback_query(lambda c: c.data.startswith("unmute_user"))
async def process_unmute_user_callback(callback: types.CallbackQuery) -> None:
    """Обрабатывает снятие ограничения с пользователя.

    Аргументы:
        callback (CallbackQuery): Callback-запрос от inline-кнопки.
    """
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Неверные данные!")
        return

    chat_id = int(parts[1])
    user_id = int(parts[2])
    bot = get_bot()

    try:
        full_permissions = types.ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True
        )
        await bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=full_permissions
        )

        chat_pk = await ChatRepository.get_chat_pk(chat_id)
        if chat_pk:
            await MutedRepository.clear_muted_till(chat_pk, user_id)

        original_text = getattr(callback.message, "html_text", callback.message.text)
        new_text = original_text + "\n<b>Ограничение снято вручную</b>"

        await callback.message.edit_text(new_text, parse_mode=ParseMode.HTML, reply_markup=None)
        await callback.answer("Ограничение снято!")

    except Exception as e:
        logger.error(f"Ошибка при снятии ограничения пользователя {user_id}: {e}")
        await callback.answer("Не удалось снять ограничение!")


@dp.callback_query(lambda c: c.data.startswith("delete_message"))
async def process_delete_message_callback(callback: types.CallbackQuery) -> None:
    """Обрабатывает удаление спам-сообщения.

    Аргументы:
        callback (CallbackQuery): Callback-запрос от inline-кнопки.
    """
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Неверные данные!")
        return

    chat_id = int(parts[1])
    msg_id = int(parts[2])
    bot = get_bot()

    try:
        await bot.delete_message(chat_id=chat_id, message_id=msg_id)

        original_text = getattr(callback.message, "html_text", callback.message.text)
        new_text = original_text + '\n\n<i>Сообщение удалено вручную</i>'

        new_markup = remove_button_from_keyboard(callback.message.reply_markup, "delete_message")
        await callback.message.edit_text(new_text, parse_mode=ParseMode.HTML, reply_markup=new_markup)

        await callback.answer("Сообщение удалено!")
        logger.info(f"Сообщение {msg_id} удалено из чата {chat_id}")

    except TelegramBadRequest as e:
        if "message to delete not found" in str(e):
            logger.warning(f"Сообщение {msg_id} в чате {chat_id} уже удалено")

            original_text = getattr(callback.message, "html_text", callback.message.text)
            new_text = original_text + '\n\n<i>Сообщение уже удалено</i>'

            new_markup = remove_button_from_keyboard(callback.message.reply_markup, "delete_message")
            await callback.message.edit_text(new_text, parse_mode=ParseMode.HTML, reply_markup=new_markup)

            await callback.answer("Сообщение уже удалено!")
        else:
            logger.error(f"Ошибка при удалении сообщения: {e}")
            await callback.answer("Не удалось удалить сообщение!")

    except Exception as e:
        logger.error(f"Ошибка при удалении сообщения: {e}")
        await callback.answer("Не удалось удалить сообщение!")


@dp.callback_query(lambda c: c.data.startswith("not_spam"))
async def process_not_spam_callback(callback: types.CallbackQuery) -> None:
    """Обрабатывает отметку сообщения как «не спам».

    Добавляет пользователя в белый список чата.

    Аргументы:
        callback (CallbackQuery): Callback-запрос от inline-кнопки.
    """
    parts = callback.data.split(":")
    if len(parts) < 3:
        await callback.answer("Неверные данные!")
        return

    try:
        chat_id = int(parts[1])
        user_id = int(parts[2])

        chat_pk = await ChatRepository.get_chat_pk(chat_id)
        if chat_pk is None:
            await callback.answer("Чат не найден!")
            return

        username = None
        if callback.message and hasattr(callback.message, 'text'):
            text = callback.message.text or callback.message.html_text or ''
            match = re.search(r'<b>Имя пользователя:</b> <code>([^<]+)</code>', text)
            if match:
                username = match.group(1)

        if not await WhitelistRepository.is_whitelisted(chat_pk, user_id):
            await WhitelistRepository.add_to_whitelist(
                chat_pk=chat_pk,
                user_id=user_id,
                username=username,
                added_by=callback.from_user.id if callback.from_user else None,
                reason="Отмечено как не спам через inline-кнопку"
            )
            logger.info(f"Пользователь {user_id} добавлен в белый список чата {chat_id}")

        original_text = getattr(callback.message, "html_text", callback.message.text)
        new_text = original_text + "\n\n<i>Отмечено как не спам. Пользователь добавлен в белый список.</i>"

        await callback.message.edit_text(new_text, parse_mode=ParseMode.HTML, reply_markup=None)
        await callback.answer("Отмечено как не спам. Пользователь добавлен в белый список.")

    except ValueError:
        await callback.answer("Неверный ID пользователя!")
    except Exception as e:
        logger.error(f"Ошибка при отметке как не спам: {e}")
        await callback.answer("Ошибка!")


@dp.callback_query(lambda c: c.data.startswith("unwhitelist"))
async def process_unwhitelist_callback(callback: types.CallbackQuery) -> None:
    """Обрабатывает нажатие на кнопку «Убрать из белого списка».

    Аргументы:
        callback (CallbackQuery): Callback-запрос от inline-кнопки.
    """
    try:
        parts = callback.data.split(":")
        if len(parts) != 3:
            await callback.answer("Неверные данные!")
            return

        chat_id = int(parts[1])
        user_id = int(parts[2])

        chat_pk = await ChatRepository.get_chat_pk(chat_id)
        if chat_pk is None:
            await callback.answer("Чат не найден!")
            return

        await WhitelistRepository.remove_from_whitelist(chat_pk, user_id)
        logger.info(f"Пользователь {user_id} удалён из белого списка чата {chat_id}")

        original_text = getattr(callback.message, "html_text", callback.message.text)
        new_text = original_text + "\n\n<i>Пользователь удалён из белого списка.</i>"

        new_markup = remove_button_from_keyboard(callback.message.reply_markup, "unwhitelist")
        await callback.message.edit_text(new_text, parse_mode=ParseMode.HTML, reply_markup=new_markup)
        await callback.answer("Пользователь удалён из белого списка!")

    except Exception as e:
        logger.error(f"Ошибка в обработчике unwhitelist: {e}")
        await callback.answer("Ошибка при удалении из белого списка!")
