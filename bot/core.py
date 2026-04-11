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
    SYSTEM_USER_IDS,
    PROXY_URL
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

    # Создание экземпляра бота (с прокси, если задан)
    session = None
    if PROXY_URL:
        from aiohttp_socks import ProxyConnector
        from aiogram.client.session.aiohttp import AiohttpSession
        connector = ProxyConnector.from_url(PROXY_URL)
        session = AiohttpSession(connector=connector)
        logger.info(f"Используется SOCKS5 прокси: {PROXY_URL.split('@')[-1] if '@' in PROXY_URL else PROXY_URL}")

    bot = Bot(token=TOKEN, session=session)
    bot_info = await bot.get_me()
    logger.info(f"Бот запущен: @{bot_info.username} (ID: {bot_info.id})")

    if TESTING:
        logger.warning("Бот запущен в ТЕСТОВОМ режиме!")

    # Закрытие общей HTTP-сессии при остановке бота
    from utils.apis import close_shared_session
    dp.shutdown.register(close_shared_session)

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
