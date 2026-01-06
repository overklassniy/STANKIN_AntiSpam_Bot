"""
Ядро бота: инициализация, константы и основные объекты.
"""

from typing import Optional

from aiogram import Bot, Dispatcher

from utils.config import (
    get_bot_token,
    TESTING,
    HELPDESK_EMAIL,
    GITHUB_URL,
    SYSTEM_USER_IDS
)
from utils.logging import logger

# Токен бота
TOKEN = get_bot_token()

# Глобальные объекты
dp = Dispatcher()
bot: Optional[Bot] = None


def get_bot() -> Bot:
    """Возвращает текущий экземпляр бота."""
    global bot
    if bot is None:
        raise RuntimeError("Бот еще не инициализирован")
    return bot


async def start_bot() -> None:
    """
    Инициализирует и запускает бота.
    """
    global bot

    # Импорт обработчиков для их регистрации
    from bot.handlers import commands, messages, callbacks  # noqa: F401
    from bot.database import init_database

    # Инициализация базы данных
    await init_database()

    # Создание экземпляра бота
    bot = Bot(token=TOKEN)
    bot_info = await bot.get_me()
    logger.info(f"Бот запущен: @{bot_info.username} (ID: {bot_info.id})")

    if TESTING:
        logger.warning("Бот запущен в ТЕСТОВОМ режиме!")

    # Запуск поллинга
    await dp.start_polling(bot, polling_timeout=30)


# Экспорт констант для обратной совместимости
__all__ = [
    'dp',
    'bot',
    'get_bot',
    'start_bot',
    'TOKEN',
    'TESTING',
    'HELPDESK_EMAIL',
    'GITHUB_URL',
    'SYSTEM_USER_IDS'
]
