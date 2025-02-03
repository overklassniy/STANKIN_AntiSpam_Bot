import asyncio
import subprocess
import threading

from waitress import serve

from bot import start_bot
from panel.app import create_app
from utils.basic import config, logger


def start_panel() -> None:
    """
    Запускает панель управления с использованием Flask.
    """
    logger.info("Запуск панели управления...")
    if config['TESTING']:
        logger.info("Запуск Flask в режиме TESTING.")
        try:
            subprocess.run([
                "flask", "--app", "panel.app", "run",
                "--host", "0.0.0.0", "--port", str(config['PANEL_PORT']), "--no-reload"
            ])
        except Exception as e:
            logger.error(f"Ошибка при запуске Flask: {e}")
    else:
        try:
            app = create_app()
            logger.info("Запуск панели через waitress (WSGI).")
            serve(app, host="0.0.0.0", port=config['PANEL_PORT'])
        except Exception as e:
            logger.error(f"Ошибка при запуске WSGI сервера: {e}")


async def main() -> None:
    """
    Единый запуск Telegram-бота и панели управления.
    """
    logger.info("Инициализация системы...")

    # Запускаем панель управления в отдельном потоке
    panel_thread = threading.Thread(target=start_panel, daemon=True)
    panel_thread.start()
    logger.info("Панель управления запущена в отдельном потоке.")

    # Запускаем Telegram-бота
    logger.info("Запуск Telegram-бота...")
    await start_bot()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Выход из приложения по команде пользователя.")
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
