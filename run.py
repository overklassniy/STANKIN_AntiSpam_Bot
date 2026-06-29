#!/usr/bin/env python3
"""STANKIN AntiSpam System — единый запуск бота и панели.

Использование:
    python run.py              # Запуск бота и панели
    python run.py --bot        # Только бот
    python run.py --panel      # Только панель
    python run.py --all        # Бот и панель (по умолчанию)

Опции:
    --bot, -b       Запустить только Telegram-бота
    --panel, -p     Запустить только веб-панель
    --all, -a       Запустить бот и панель (по умолчанию)
    --help, -h      Показать справку
"""

import argparse
import asyncio
import os
import signal
import sys
from enum import Enum

from core.logging import logger, get_uvicorn_log_config
from core.sentry import init_sentry


class RunMode(Enum):
    ALL = 'all'
    BOT = 'bot'
    PANEL = 'panel'


def parse_args() -> RunMode:
    """Парсит аргументы командной строки.

    Возвращаемое значение:
        mode (RunMode): Режим запуска.
    """
    parser = argparse.ArgumentParser(
        description='STANKIN AntiSpam System Launcher',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python run.py              Запуск бота и панели
  python run.py --bot        Только бот
  python run.py --panel      Только панель
        """
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--bot', '-b', action='store_true', help='Запустить только Telegram-бота')
    group.add_argument('--panel', '-p', action='store_true', help='Запустить только веб-панель')
    group.add_argument('--all', '-a', action='store_true', default=True, help='Запустить бот и панель (по умолчанию)')

    args = parser.parse_args()

    if args.bot:
        return RunMode.BOT
    elif args.panel:
        return RunMode.PANEL
    else:
        return RunMode.ALL


def setup_directories() -> None:
    """Создаёт необходимые директории для логов и данных."""
    from core.config import LOGS_DIR

    os.makedirs(LOGS_DIR, exist_ok=True)
    os.makedirs('data', exist_ok=True)


async def start_bot_async() -> None:
    """Запускает Telegram-бота асинхронно."""
    from bot.core import start_bot

    logger.info("Запуск Telegram-бота...")
    await start_bot()


async def start_panel_async() -> uvicorn.Server:
    """Запускает FastAPI панель асинхронно в том же event loop.

    Возвращаемое значение:
        server (uvicorn.Server): Экземпляр сервера для управления остановкой.
    """
    import uvicorn
    from panel.app import create_app
    from core.config import PANEL_PORT, TESTING

    logger.info("Запуск веб-панели...")

    app = create_app()

    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=PANEL_PORT,
        log_level="info" if not TESTING else "debug",
        loop="asyncio",
        log_config=get_uvicorn_log_config(),
    )
    server = uvicorn.Server(config)
    server.install_signal_handlers = lambda: None
    await server.serve()
    return server


async def run_all() -> None:
    """Запускает бот и панель одновременно в одном event loop."""
    setup_directories()

    logger.info("STANKIN AntiSpam System")
    logger.info("Режим: бот + панель")

    import uvicorn
    from panel.app import create_app
    from core.config import PANEL_PORT, TESTING

    app = create_app()
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=PANEL_PORT,
        log_level="info" if not TESTING else "debug",
        loop="asyncio",
        log_config=get_uvicorn_log_config(),
    )
    server = uvicorn.Server(config)
    server.install_signal_handlers = lambda: None

    bot_task = asyncio.create_task(start_bot_async())
    panel_task = asyncio.create_task(server.serve())

    # Обработчик сигналов для корректного завершения
    loop = asyncio.get_running_loop()

    def _signal_handler() -> None:
        logger.info("Получен сигнал остановки...")
        server.should_exit = True
        bot_task.cancel()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _signal_handler)

    await asyncio.gather(bot_task, panel_task, return_exceptions=True)


async def run_bot_only() -> None:
    """Запускает только бота."""
    logger.info("STANKIN AntiSpam System")
    logger.info("Режим: только бот")

    setup_directories()
    await start_bot_async()


async def run_panel_only() -> None:
    """Запускает только панель."""
    logger.info("STANKIN AntiSpam System")
    logger.info("Режим: только панель")

    setup_directories()
    await start_panel_async()


def main() -> None:
    """Главная функция запуска."""
    init_sentry()
    mode = parse_args()

    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        if mode == RunMode.BOT:
            asyncio.run(run_bot_only())
        elif mode == RunMode.PANEL:
            asyncio.run(run_panel_only())
        else:
            asyncio.run(run_all())

    except KeyboardInterrupt:
        logger.info("Выход по команде пользователя (Ctrl+C).")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
