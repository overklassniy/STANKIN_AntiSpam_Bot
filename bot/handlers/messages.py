"""
Обработчик сообщений для проверки на спам.
"""

import os
from datetime import datetime
from typing import Union

from aiogram import types

from bot.core import dp, get_bot, SYSTEM_USER_IDS
from bot.database import (
    get_muted_user, create_muted_user, update_muted_user,
    add_spam_message, add_collected_message, get_setting
)
from bot.keyboards import create_spam_notification_keyboard
from bot.notifications import (
    format_spam_notification,
    send_spam_notification,
    send_mute_notification
)
from utils.config import (
    TARGET_CHAT_ID, TESTING,
    NOTIFICATION_CHAT_94_SPAM_THREAD,
    NOTIFICATION_CHAT_98_SPAM_THREAD,
    NOTIFICATION_CHAT_NS_SPAM_THREAD
)
from utils.helpers import add_hours_get_timestamp
from utils.logging import logger


async def check_if_admin(chat_id: int, user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором чата."""
    bot = get_bot()
    try:
        member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        return member.status in ["administrator", "creator"] or user_id in SYSTEM_USER_IDS
    except Exception as e:
        logger.error(f"Ошибка при проверке статуса пользователя {user_id}: {e}")
        return False


async def analyze_message(text: str, author_id: int) -> dict:
    """
    Анализирует сообщение на спам.

    Returns:
        dict с ключами: is_spam, ausure, bert_prediction, cas, lols, chatgpt, has_email
    """
    from utils.text import contains_email

    result = {
        "is_spam": False,
        "ausure": False,
        "bert_prediction": (0, [0.5, 0.5]),
        "cas": None,
        "lols": None,
        "chatgpt": None,
        "has_email": contains_email(text)
    }

    # Получаем настройки из БД
    bert_threshold = await get_setting('BERT_THRESHOLD', 0.945)
    bert_sure_threshold = await get_setting('BERT_SURE_THRESHOLD', 0.98)
    check_cas = await get_setting('CHECK_CAS', True)
    check_lols = await get_setting('CHECK_LOLS', True)
    enable_chatgpt = await get_setting('ENABLE_CHATGPT', False)

    # Проверка через BERT
    from utils.ml import bert_predict
    result["bert_prediction"] = bert_predict(text, bert_threshold)

    # Определяем уровень уверенности
    if result["bert_prediction"][0] and (max(result["bert_prediction"][1]) > bert_sure_threshold):
        result["ausure"] = True

    # Проверка через внешние API
    if check_cas:
        from utils.apis import get_cas_async
        result["cas"] = await get_cas_async(author_id)

    if check_lols:
        from utils.apis import get_lols_async
        result["lols"] = await get_lols_async(author_id)

    # Проверка через ChatGPT (опционально)
    if enable_chatgpt and os.getenv('OPENAI_API_KEY'):
        from utils.ml import chatgpt_predict
        result["chatgpt"] = await chatgpt_predict(text)

    return result


def determine_spam_status(
    analysis: dict,
    has_reply_markup: bool
) -> Union[bool, str]:
    """
    Определяет статус спама на основе анализа.

    Returns:
        True - спам
        "NS" - частичный спам (содержит email)
        False - не спам
    """
    if has_reply_markup:
        return True

    if analysis["has_email"]:
        if bool(analysis["bert_prediction"][0]):
            return "NS"
        return False

    if bool(analysis["bert_prediction"][0]):
        return True

    if analysis["cas"] or analysis["lols"] or analysis["chatgpt"]:
        return True

    return False


def get_notification_thread(is_spam: Union[bool, str], ausure: bool) -> int:
    """Определяет тред для уведомления."""
    if is_spam == "NS":
        return NOTIFICATION_CHAT_NS_SPAM_THREAD
    elif is_spam is True and ausure:
        return NOTIFICATION_CHAT_98_SPAM_THREAD
    else:
        return NOTIFICATION_CHAT_94_SPAM_THREAD


@dp.message()
async def handle_message(message: types.Message) -> None:
    """
    Главный обработчик сообщений для проверки на спам.
    """
    # Проверяем, что сообщение из целевого чата
    if message.chat.id != TARGET_CHAT_ID:
        return

    author = message.from_user
    author_id = author.id
    author_name = author.username

    # Получаем настройки
    collect_all = await get_setting('COLLECT_ALL_MESSAGES', False)

    # Сбор сообщений (если включено)
    if collect_all and message.text:
        try:
            await add_collected_message(
                chat_id=message.chat.id,
                user_id=author_id,
                username=author_name,
                message_text=message.text
            )
        except Exception as e:
            logger.error(f"Ошибка при сохранении сообщения: {e}")

    logger.info(f"Обработка сообщения от {author_id} в чате {TARGET_CHAT_ID}")

    try:
        # Пропускаем сообщения от администраторов
        is_admin = await check_if_admin(TARGET_CHAT_ID, author_id)

        # В тестовом режиме проверяем все сообщения
        if TESTING:
            is_admin = False

        if is_admin:
            logger.debug(f"Сообщение от администратора {author_id} пропускается")
            return

        # Проверяем белый список
        from bot.database import is_whitelisted
        if await is_whitelisted(author_id):
            logger.debug(f"Сообщение от пользователя {author_id} в белом списке - пропускается")
            return

        # Получаем текст сообщения
        message_text = message.text or message.caption
        if not message_text:
            logger.debug(f"Сообщение от {author_id} без текста - игнорируется")
            return

        # Проверяем наличие inline клавиатуры
        check_reply_markup = await get_setting('CHECK_REPLY_MARKUP', True)
        has_reply_markup = bool(message.reply_markup) if check_reply_markup else None

        # Анализируем сообщение
        analysis = await analyze_message(message_text, author_id)

        # Определяем статус спама
        is_spam = determine_spam_status(analysis, has_reply_markup or False)

        if not is_spam:
            logger.debug(f"Сообщение от {author_id} не является спамом")
            return

        logger.info(f"Сообщение от {author_id} идентифицировано как спам (ausure={analysis['ausure']})")

        # Определяем тред для уведомления
        notification_thread = get_notification_thread(is_spam, analysis["ausure"])

        # Сохраняем в БД
        current_timestamp = datetime.now().timestamp()
        bert_score = round(analysis["bert_prediction"][1][1], 7)

        await add_spam_message(
            timestamp=current_timestamp,
            author_id=author_id,
            author_username=author_name,
            message_text=message_text,
            has_reply_markup=has_reply_markup,
            cas=analysis["cas"],
            lols=analysis["lols"],
            chatgpt_prediction=analysis["chatgpt"],
            bert_prediction=bert_score
        )

        # Настройки автоматических действий
        enable_deleting = await get_setting('ENABLE_DELETING', True)
        enable_automuting = await get_setting('ENABLE_AUTOMUTING', False)
        ausure = analysis["ausure"]

        # Авто-удаление (только при высокой уверенности)
        auto_deleted = False
        if enable_deleting and is_spam is True and ausure:
            try:
                await message.delete()
                auto_deleted = True
                logger.info(f"Сообщение от {author_id} автоматически удалено")
            except Exception as e:
                logger.error(f"Ошибка при автоматическом удалении: {e}")

        # Обработка записи о нарушениях
        muted = await get_muted_user(author_id)
        if not muted:
            relapse = 1
            until = add_hours_get_timestamp(24) if (enable_automuting and ausure) else None
            await create_muted_user(author_id, author_name, current_timestamp, until, relapse)
        else:
            relapse = muted['relapse_number'] + 1
            hours = 168 if relapse == 2 else 999
            until = add_hours_get_timestamp(hours) if (enable_automuting and ausure) else muted.get('muted_till_timestamp')
            await update_muted_user(author_id, current_timestamp, until, relapse)

        # Формируем уведомление
        muted_until_str = None
        if until and ausure and enable_automuting:
            muted_until_str = datetime.fromtimestamp(until).strftime("%d.%m.%Y %H:%M:%S")

        notification_text = format_spam_notification(
            timestamp=current_timestamp,
            author_id=author_id,
            author_name=author_name,
            message_text=message_text,
            has_reply_markup=has_reply_markup,
            bert_score=bert_score,
            relapse_number=relapse,
            auto_deleted=auto_deleted,
            muted_until=muted_until_str
        )

        # Авто-мьютинг (только при высокой уверенности)
        mute_success = False
        if enable_automuting and enable_deleting and ausure:
            bot = get_bot()
            try:
                await bot.restrict_chat_member(
                    chat_id=TARGET_CHAT_ID,
                    user_id=author_id,
                    permissions=types.ChatPermissions(can_send_messages=False),
                    until_date=until
                )
                logger.info(f"Пользователь {author_id} автоматически ограничен до {muted_until_str}")
                mute_success = True
            except Exception as e:
                logger.error(f"Ошибка при автоматическом ограничении {author_id}: {e}")

        # Отправляем уведомления
        if enable_automuting and enable_deleting and ausure and mute_success:
            # Автоматические действия выполнены успешно - отправляем уведомления без кнопок
            notification_sent = await send_spam_notification(
                notification_thread, notification_text, keyboard=None
            )
            if not notification_sent:
                logger.warning(f"Не удалось отправить уведомление о спаме для {author_id}")
            
            mute_notification_sent = await send_mute_notification(
                author_id, author_name, muted_until_str, relapse
            )
            if not mute_notification_sent:
                logger.warning(f"Не удалось отправить уведомление об ограничении для {author_id}")
        else:
            # Автоматические действия не выполнены или не включены - отправляем с кнопками
            keyboard = create_spam_notification_keyboard(
                message_id=message.message_id,
                user_id=author_id,
                include_delete=not auto_deleted,
                include_mute=True,
                include_not_spam=True
            )
            notification_sent = await send_spam_notification(
                notification_thread, notification_text, keyboard=keyboard
            )
            if not notification_sent:
                logger.warning(f"Не удалось отправить уведомление о спаме для {author_id}")

    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения в чате {TARGET_CHAT_ID}: {e}")
