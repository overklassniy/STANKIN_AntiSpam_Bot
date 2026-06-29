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
