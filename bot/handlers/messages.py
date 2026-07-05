"""Обработчик сообщений для модерации.

Бот обрабатывает сообщения во всех наблюдаемых чатах, где он админ.
В наблюдаемых чатах бот не отправляет никаких сообщений — только модерация.
"""

from aiogram import F
from aiogram.types import Message

from bot.core import dp, get_bot
from bot.services.moderation import ModerationService


@dp.message(F.text | F.caption)
async def handle_message(message: Message) -> None:
    """Главный обработчик сообщений для проверки на спам.

    Обрабатывает сообщения во всех наблюдаемых чатах.
    В наблюдаемых чатах бот молчит — никакие сообщения не отправляются.

    Аргументы:
        message (Message): Входящее сообщение Telegram.
    """
    bot = get_bot()
    await ModerationService.handle_message(message, bot)


@dp.edited_message(F.text | F.caption)
async def handle_edited_message(message: Message) -> None:
    """Обработчик отредактированных сообщений для проверки на спам.

    Проверяет отредактированные сообщения, если в настройках чата включена опция CHECK_EDITED_MESSAGES.
    В наблюдаемых чатах бот молчит — никакие сообщения не отправляются.

    Аргументы:
        message (Message): Отредактированное сообщение Telegram.
    """
    bot = get_bot()
    await ModerationService.handle_message(message, bot, is_edited=True)
