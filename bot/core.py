"""Ядро бота: инициализация, константы и основные объекты."""

from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.types import ErrorEvent as TelegramErrorEvent

from core.config import (
    get_bot_token,
    TESTING,
    HELPDESK_EMAIL,
    GITHUB_URL,
    SYSTEM_USER_IDS,
    PROXY_URL,
    DATABASE_URL,
    NOTIFICATION_CHAT_ID,
)
from core.logging import logger
from core.sentry import capture_exception

# Токен бота
TOKEN = get_bot_token()

# Глобальные объекты
dp = Dispatcher()
bot: Optional[Bot] = None
bot_username: Optional[str] = None


@dp.errors()
async def on_error(event: TelegramErrorEvent) -> None:
    """Глобальный обработчик ошибок диспетчера.

    Логирует и отправляет неперехваченные исключения в Sentry.

    Аргументы:
        event (TelegramErrorEvent): Событие ошибки aiogram.
    """
    exc = event.exception
    logger.error(f"Ошибка в обработчике: {exc}", exc_info=exc)
    capture_exception(exc)


def get_bot() -> Bot:
    """Возвращает текущий экземпляр бота.

    Возвращаемое значение:
        bot (Bot): Экземпляр бота.

    Исключения:
        RuntimeError: Если бот ещё не инициализирован.
    """
    global bot
    if bot is None:
        raise RuntimeError("Бот еще не инициализирован")
    return bot


async def start_bot() -> None:
    """Инициализирует и запускает бота.

    Алгоритм работы:
        1. Инициализировать пул соединений PostgreSQL.
        2. Инициализировать настройки по умолчанию.
        3. Создать экземпляр бота.
        4. Обнаружить чаты, где бот админ.
        5. Зарегистрировать обработчики.
        6. Запустить поллинг.
    """
    global bot, bot_username

    # Инициализация пула PostgreSQL
    from core.db import init_pool, close_pool
    from core.repository.settings import SettingsRepository
    from bot.services.chat_discovery import discover_admin_chats

    await init_pool(DATABASE_URL)
    await SettingsRepository.init_default_global_settings()

    # Импорт обработчиков для их регистрации
    from bot.handlers import commands, messages, callbacks  # noqa: F401

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
    bot_username = bot_info.username
    logger.info(f"Бот запущен: @{bot_info.username} (ID: {bot_info.id})")

    if TESTING:
        logger.warning("Бот запущен в ТЕСТОВОМ режиме!")

    # Автообнаружение чатов, где бот админ
    await discover_admin_chats(bot, exclude_chat_id=NOTIFICATION_CHAT_ID)

    # Запуск планировщика авто-бэкапов
    from bot.services.backup import BackupService
    await BackupService.start_scheduler()

    # Закрытие ресурсов при остановке
    from bot.services.external_apis import close_shared_session
    dp.shutdown.register(BackupService.stop_scheduler)
    dp.shutdown.register(close_shared_session)
    dp.shutdown.register(close_pool)

    # Запуск поллинга
    await dp.start_polling(bot, polling_timeout=30, handle_signals=False)


__all__ = [
    'dp',
    'bot',
    'bot_username',
    'get_bot',
    'start_bot',
    'TOKEN',
    'TESTING',
    'HELPDESK_EMAIL',
    'GITHUB_URL',
    'SYSTEM_USER_IDS'
]
