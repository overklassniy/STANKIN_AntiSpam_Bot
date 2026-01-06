#!/usr/bin/env python3
"""
STANKIN AntiSpam System - Unified Launcher

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
import threading
from enum import Enum
from typing import Optional

from waitress import serve


class RunMode(Enum):
    ALL = 'all'
    BOT = 'bot'
    PANEL = 'panel'


def parse_args() -> RunMode:
    """Парсит аргументы командной строки."""
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
    group.add_argument(
        '--bot', '-b',
        action='store_true',
        help='Запустить только Telegram-бота'
    )
    group.add_argument(
        '--panel', '-p',
        action='store_true',
        help='Запустить только веб-панель'
    )
    group.add_argument(
        '--all', '-a',
        action='store_true',
        default=True,
        help='Запустить бот и панель (по умолчанию)'
    )

    args = parser.parse_args()

    if args.bot:
        return RunMode.BOT
    elif args.panel:
        return RunMode.PANEL
    else:
        return RunMode.ALL


def setup_directories() -> None:
    """Создает необходимые директории."""
    from utils.config import LOGS_DIR, DATABASE_DIR

    os.makedirs(LOGS_DIR, exist_ok=True)
    os.makedirs(DATABASE_DIR, exist_ok=True)
    os.makedirs('data', exist_ok=True)


def start_panel() -> None:
    """
    Запускает панель управления.
    """
    from panel.app import create_app
    from utils.config import PANEL_PORT, TESTING
    from utils.logging import logger

    logger.info("Запуск панели управления...")

    try:
        app = create_app()

        if TESTING:
            logger.info("Запуск Flask в режиме тестирования.")
            app.run(
                host="0.0.0.0",
                port=PANEL_PORT,
                debug=False,
                use_reloader=False,
                threaded=True
            )
        else:
            logger.info(f"Запуск панели через Waitress на порту {PANEL_PORT}.")
            serve(
                app,
                host="0.0.0.0",
                port=PANEL_PORT,
                threads=4,
                connection_limit=100,
                channel_timeout=120
            )
    except Exception as e:
        from utils.logging import logger
        logger.error(f"Ошибка при запуске панели: {e}")
        raise


async def start_bot_async() -> None:
    """
    Запускает Telegram-бота асинхронно.
    """
    from bot.core import start_bot
    from utils.logging import logger

    logger.info("Запуск Telegram-бота...")
    await start_bot()


async def run_all() -> None:
    """
    Запускает бот и панель одновременно.
    """
    from utils.logging import logger

    setup_directories()

    logger.info("=" * 60)
    logger.info("STANKIN AntiSpam System")
    logger.info("Режим: бот + панель")
    logger.info("=" * 60)

    # Запускаем панель в отдельном потоке
    panel_thread = threading.Thread(
        target=start_panel,
        daemon=True,
        name="PanelThread"
    )
    panel_thread.start()
    logger.info("Панель запущена в отдельном потоке.")

    # Запускаем бота
    await start_bot_async()


async def run_bot_only() -> None:
    """
    Запускает только бота.
    """
    from utils.logging import logger

    logger.info("=" * 60)
    logger.info("STANKIN AntiSpam System")
    logger.info("Режим: только бот")
    logger.info("=" * 60)

    setup_directories()
    await start_bot_async()


def run_panel_only() -> None:
    """
    Запускает только панель.
    """
    from utils.logging import logger

    logger.info("=" * 60)
    logger.info("STANKIN AntiSpam System")
    logger.info("Режим: только панель")
    logger.info("=" * 60)

    setup_directories()
    start_panel()


def main() -> None:
    """
    Главная функция запуска.
    """
    mode = parse_args()

    # Для Windows используем специальную политику для asyncio
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        if mode == RunMode.BOT:
            asyncio.run(run_bot_only())
        elif mode == RunMode.PANEL:
            run_panel_only()
        else:  # RunMode.ALL
            asyncio.run(run_all())

    except KeyboardInterrupt:
        print("\nВыход по команде пользователя (Ctrl+C).")
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
