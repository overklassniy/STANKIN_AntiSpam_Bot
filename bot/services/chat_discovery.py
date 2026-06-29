"""Автообнаружение чатов, где бот является администратором."""

from typing import Optional

from aiogram import Bot
from aiogram.types import Chat

from core.repository.chat import ChatRepository
from core.config import NOTIFICATION_CHAT_ID
from core.logging import logger


async def discover_admin_chats(bot: Bot, exclude_chat_id: Optional[int] = None) -> None:
    """Обнаруживает все чаты, где бот админ, и сохраняет их в БД.

    Алгоритм работы:
        1. Получить список обновлений бота.
        2. Для каждого чата проверить статус бота.
        3. Если бот админ — добавить в наблюдаемые.
        4. Исключить чат управления.

    Аргументы:
        bot (Bot): Экземпляр бота aiogram.
        exclude_chat_id (Optional[int]): ID чата, который нужно исключить (чат управления).
    """
    if exclude_chat_id is None:
        exclude_chat_id = NOTIFICATION_CHAT_ID

    bot_info = await bot.get_me()
    bot_id = bot_info.id

    discovered = 0

    # Получаем обновления для поиска чатов
    try:
        updates = await bot.get_updates(offset=-1, limit=100)
    except Exception as e:
        logger.warning(f"Не удалось получить обновления для обнаружения чатов: {e}")
        return

    seen_chat_ids = set()

    for update in updates:
        chat = None
        if update.message:
            chat = update.message.chat
        elif update.edited_message:
            chat = update.edited_message.chat
        elif update.my_chat_member:
            chat = update.my_chat_member.chat
        elif update.channel_post:
            chat = update.channel_post.chat

        if chat and chat.id not in seen_chat_ids:
            seen_chat_ids.add(chat.id)

            if chat.id == exclude_chat_id:
                continue

            # Проверяем, является ли бот админом в этом чате
            try:
                member = await bot.get_chat_member(chat.id, bot_id)
                if member.status == 'administrator':
                    await ChatRepository.add_chat(chat.id, chat.title)
                    discovered += 1
                    logger.info(f"Чат обнаружен: {chat.title} ({chat.id})")
            except Exception:
                pass

    # Также проверяем уже существующие в БД чаты
    active_chats = await ChatRepository.get_active_chats()
    for chat_record in active_chats:
        if chat_record['chat_id'] in seen_chat_ids:
            continue
        if chat_record['chat_id'] == exclude_chat_id:
            continue

        try:
            member = await bot.get_chat_member(chat_record['chat_id'], bot_id)
            if member.status != 'administrator':
                await ChatRepository.deactivate_chat(chat_record['chat_id'])
                logger.info(f"Чат деактивирован (бот больше не админ): {chat_record['title']} ({chat_record['chat_id']})")
            else:
                discovered += 1
        except Exception:
            await ChatRepository.deactivate_chat(chat_record['chat_id'])
            logger.warning(f"Чат недоступен, деактивирован: {chat_record['chat_id']}")

    logger.info(f"Обнаружение чатов завершено. Активных чатов: {discovered}")
