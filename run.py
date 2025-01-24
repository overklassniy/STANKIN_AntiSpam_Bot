import asyncio
import subprocess
import threading

from bot import start_bot  # Импорт функции запуска бота
from utils.basic import config  # Убедитесь, что путь указан верно


def start_panel():
    """
    Запускает панель управления с использованием команды flask run.
    """
    # Команда для запуска Flask с помощью subprocess
    subprocess.run(["flask", "--app", "panel.app", "run", "--host", "0.0.0.0", "--port", str(config['PANEL_PORT'])])


async def main():
    """
    Единый запуск Telegram-бота и панели управления.
    """
    # Запускаем панель управления в отдельном потоке
    panel_thread = threading.Thread(target=start_panel)
    panel_thread.daemon = True
    panel_thread.start()

    # Запускаем Telegram-бота
    await start_bot()


if __name__ == '__main__':
    asyncio.run(main())
