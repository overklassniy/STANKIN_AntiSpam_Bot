"""
Обработчики callback-запросов (нажатия на inline-кнопки).
"""

from datetime import datetime

from aiogram import types
from aiogram.enums import ParseMode

from bot.core import dp, get_bot
from bot.database import get_muted_user, update_muted_user, clear_muted_user_timestamp
from bot.keyboards import remove_button_from_keyboard
from bot.notifications import send_mute_notification
from utils.config import TARGET_CHAT_ID
from utils.helpers import add_hours_get_timestamp
from utils.logging import logger


@dp.callback_query(lambda c: c.data.startswith("mute_user"))
async def process_mute_user_callback(callback: types.CallbackQuery) -> None:
    """
    Обрабатывает нажатие на кнопку "Ограничить пользователя".
    """
    try:
        parts = callback.data.split(":")
        if len(parts) != 2:
            await callback.answer("Неверные данные!")
            return

        user_id = int(parts[1])
        bot = get_bot()

        # Получаем данные пользователя
        muted_user = await get_muted_user(user_id)
        if not muted_user:
            await callback.answer("Пользователь не найден в базе данных!")
            return

        relapse_number = muted_user['relapse_number']
        username = muted_user['username']

        # Определяем время ограничения
        if relapse_number == 1:
            until_timestamp = add_hours_get_timestamp(24)
        elif relapse_number == 2:
            until_timestamp = add_hours_get_timestamp(168)
        else:
            until_timestamp = add_hours_get_timestamp(999)

        # Обновляем БД
        await update_muted_user(
            user_id,
            datetime.now().timestamp(),
            until_timestamp,
            relapse_number
        )

        # Применяем ограничение в Telegram
        mute_permissions = types.ChatPermissions(can_send_messages=False)
        await bot.restrict_chat_member(
            chat_id=TARGET_CHAT_ID,
            user_id=user_id,
            permissions=mute_permissions,
            until_date=until_timestamp
        )

        until_str = datetime.fromtimestamp(until_timestamp).strftime("%d.%m.%Y %H:%M:%S")

        # Обновляем сообщение с уведомлением
        original_text = getattr(callback.message, "html_text", callback.message.text)
        new_text = original_text + f'\n<b>Ограничен до:</b> {until_str}'

        new_markup = remove_button_from_keyboard(callback.message.reply_markup, "mute_user")
        await callback.message.edit_text(new_text, parse_mode=ParseMode.HTML, reply_markup=new_markup)

        await callback.answer("Пользователь ограничен!")
        logger.info(f"Пользователь {user_id} ограничен до {until_str} (Рецидив №{relapse_number})")

        # Отправляем уведомление в тред ограниченных
        await send_mute_notification(user_id, username, until_str, relapse_number)

    except Exception as e:
        logger.error(f"Ошибка в обработчике mute_user: {e}")
        await callback.answer("Ошибка при ограничении пользователя!")


@dp.callback_query(lambda c: c.data.startswith("unmute_user"))
async def process_unmute_user_callback(callback: types.CallbackQuery) -> None:
    """
    Обрабатывает снятие ограничения с пользователя.
    """
    parts = callback.data.split(":")
    if len(parts) != 2:
        await callback.answer("Неверные данные!")
        return

    user_id = int(parts[1])
    bot = get_bot()

    try:
        # Снимаем ограничения в Telegram
        full_permissions = types.ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True
        )
        await bot.restrict_chat_member(
            chat_id=TARGET_CHAT_ID,
            user_id=user_id,
            permissions=full_permissions
        )

        # Обновляем БД
        await clear_muted_user_timestamp(user_id)

        # Обновляем уведомление
        original_text = getattr(callback.message, "html_text", callback.message.text)
        new_text = original_text + "\n<b>Ограничение снято вручную</b>"

        await callback.message.edit_text(new_text, parse_mode=ParseMode.HTML, reply_markup=None)
        await callback.answer("Ограничение снято!")

    except Exception as e:
        logger.error(f"Ошибка при снятии ограничения пользователя {user_id}: {e}")
        await callback.answer("Не удалось снять ограничение!")


@dp.callback_query(lambda c: c.data.startswith("delete_message"))
async def process_delete_message_callback(callback: types.CallbackQuery) -> None:
    """
    Обрабатывает удаление спам-сообщения.
    """
    parts = callback.data.split(":")
    if len(parts) != 2:
        await callback.answer("Неверные данные!")
        return

    msg_id = int(parts[1])
    bot = get_bot()

    try:
        await bot.delete_message(chat_id=TARGET_CHAT_ID, message_id=msg_id)

        original_text = getattr(callback.message, "html_text", callback.message.text)
        new_text = original_text + '\n\n<i>Сообщение удалено вручную</i>'

        new_markup = remove_button_from_keyboard(callback.message.reply_markup, "delete_message")
        await callback.message.edit_text(new_text, parse_mode=ParseMode.HTML, reply_markup=new_markup)

        await callback.answer("Сообщение удалено!")
        logger.info(f"Сообщение {msg_id} удалено из чата {TARGET_CHAT_ID}")

    except Exception as e:
        logger.error(f"Ошибка при удалении сообщения: {e}")
        await callback.answer("Не удалось удалить сообщение!")


@dp.callback_query(lambda c: c.data.startswith("not_spam"))
async def process_not_spam_callback(callback: types.CallbackQuery) -> None:
    """
    Обрабатывает отметку сообщения как "не спам".
    Добавляет пользователя в белый список.
    """
    parts = callback.data.split(":")
    if len(parts) < 2:
        await callback.answer("Неверные данные!")
        return

    try:
        user_id = int(parts[1])
        
        # Добавляем пользователя в белый список
        from bot.database import add_to_whitelist, is_whitelisted
        
        # Получаем username из сообщения, если возможно
        username = None
        if callback.message and hasattr(callback.message, 'text'):
            # Пытаемся извлечь username из текста уведомления
            text = callback.message.text or callback.message.html_text or ''
            import re
            match = re.search(r'<b>Имя пользователя:</b> <code>([^<]+)</code>', text)
            if match:
                username = match.group(1)
        
        # Проверяем, не добавлен ли уже
        if not await is_whitelisted(user_id):
            await add_to_whitelist(
                user_id=user_id,
                username=username,
                added_by=callback.from_user.id if callback.from_user else None,
                reason="Отмечено как не спам через панель"
            )
            logger.info(f"Пользователь {user_id} добавлен в белый список")

        original_text = getattr(callback.message, "html_text", callback.message.text)
        new_text = original_text + "\n\n<i>✅ Отмечено как не спам. Пользователь добавлен в белый список.</i>"

        await callback.message.edit_text(new_text, parse_mode=ParseMode.HTML, reply_markup=None)
        await callback.answer("Отмечено как не спам. Пользователь добавлен в белый список.")
        logger.info(f"Сообщение отмечено как не спам, пользователь {user_id} добавлен в белый список")

    except ValueError:
        await callback.answer("Неверный ID пользователя!")
    except Exception as e:
        logger.error(f"Ошибка при отметке как не спам: {e}")
        await callback.answer("Ошибка!")
