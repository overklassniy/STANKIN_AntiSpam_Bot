"""Сервис резервного копирования базы данных.

Создаёт дамп базы данных через pg_dump, вычисляет SHA-256 хеш
и отправляет файл в Telegram-чат управления в указанный тред.
"""

import asyncio
import hashlib
import os
import tempfile
from datetime import datetime, timedelta
from typing import Optional, Tuple
from urllib.parse import urlparse

from core.config import (
    DATABASE_URL,
    NOTIFICATION_CHAT_ID,
    NOTIFICATION_CHAT_BACKUP_THREAD,
)
from core.logging import logger


class BackupService:
    """Сервис создания и отправки резервных копий базы данных."""

    _scheduler_task: Optional[asyncio.Task] = None

    @staticmethod
    def _parse_db_url(url: str) -> dict:
        """Разбирает строку подключения PostgreSQL на компоненты.

        Аргументы:
            url (str): Строка подключения вида postgresql://user:pass@host:port/db.

        Возвращаемое значение:
            dict: Словарь с ключами host, port, user, password, dbname.
        """
        parsed = urlparse(url)
        return {
            'host': parsed.hostname or 'localhost',
            'port': str(parsed.port or 5432),
            'user': parsed.username or 'postgres',
            'password': parsed.password or '',
            'dbname': parsed.path.lstrip('/'),
        }

    @staticmethod
    async def create_backup(output_dir: Optional[str] = None) -> Tuple[str, str]:
        """Создаёт дамп базы данных через pg_dump и вычисляет SHA-256 хеш.

        Аргументы:
            output_dir (Optional[str]): Директория для файла дампа.
                Если не указана, используется системная временная директория.

        Возвращаемое значение:
            tuple: (путь_к_файлу, sha256_хеш).

        Исключения:
            FileNotFoundError: Если pg_dump не найден в системе.
            RuntimeError: Если pg_dump завершился с ошибкой.
        """
        params = BackupService._parse_db_url(DATABASE_URL)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'backup_{timestamp}.sql'

        if output_dir is None:
            output_dir = tempfile.gettempdir()

        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)

        env = os.environ.copy()
        env['PGPASSWORD'] = params['password']

        cmd = [
            'pg_dump',
            '-h', params['host'],
            '-p', params['port'],
            '-U', params['user'],
            '-d', params['dbname'],
            '-f', filepath,
        ]

        logger.info(f'Запуск pg_dump для базы {params["dbname"]} на {params["host"]}:{params["port"]}')

        process = await asyncio.create_subprocess_exec(
            *cmd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode().strip() if stderr else 'Неизвестная ошибка'
            raise RuntimeError(f'pg_dump завершился с ошибкой: {error_msg}')

        sha256 = hashlib.sha256()
        with open(filepath, 'rb') as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                sha256.update(chunk)

        hash_str = sha256.hexdigest()
        file_size = os.path.getsize(filepath)
        logger.info(f'Дамп создан: {filepath} ({file_size} байт), SHA-256: {hash_str}')

        return filepath, hash_str

    @staticmethod
    async def send_backup_to_telegram(filepath: str, hash_str: str) -> bool:
        """Отправляет файл дампа в Telegram-чат управления.

        Аргументы:
            filepath (str): Путь к файлу дампа.
            hash_str (str): SHA-256 хеш файла.

        Возвращаемое значение:
            bool: True если отправлено успешно.
        """
        from bot.core import get_bot
        from aiogram.types import FSInputFile

        if not NOTIFICATION_CHAT_ID:
            logger.error('NOTIFICATION_CHAT_ID не задан, отправка бэкапа невозможна')
            return False

        bot = get_bot()
        filename = os.path.basename(filepath)
        file_size = os.path.getsize(filepath)

        caption = (
            f'<b>Резервная копия базы данных</b>\n'
            f'<b>Файл:</b> <code>{filename}</code>\n'
            f'<b>Размер:</b> {file_size} байт\n'
            f'<b>SHA-256:</b> <code>{hash_str}</code>\n'
            f'<b>Дата:</b> {datetime.now().strftime("%d.%m.%Y %H:%M:%S")}'
        )

        try:
            document = FSInputFile(filepath, filename=filename)
            await bot.send_document(
                chat_id=NOTIFICATION_CHAT_ID,
                document=document,
                caption=caption,
                parse_mode='HTML',
                message_thread_id=NOTIFICATION_CHAT_BACKUP_THREAD,
            )
            logger.info('Бэкап отправлен в Telegram')
            return True
        except Exception as e:
            logger.error(f'Ошибка отправки бэкапа в Telegram: {e}')
            return False
        finally:
            try:
                os.remove(filepath)
            except OSError:
                pass

    @staticmethod
    async def run_backup() -> bool:
        """Создаёт дамп базы данных и отправляет его в Telegram.

        Возвращаемое значение:
            bool: True если успешно.
        """
        try:
            filepath, hash_str = await BackupService.create_backup()
            return await BackupService.send_backup_to_telegram(filepath, hash_str)
        except FileNotFoundError:
            logger.error('pg_dump не найден. Установите postgresql-client в систему.')
            return False
        except Exception as e:
            logger.error(f'Ошибка создания бэкапа: {e}')
            return False

    @staticmethod
    async def start_scheduler() -> None:
        """Запускает планировщик автоматического резервного копирования.

        Читает настройки BACKUP_ENABLED, BACKUP_START_TIME, BACKUP_INTERVAL_HOURS
        из базы данных. Если авто-бэкап включён, запускает фоновую задачу.
        """
        from core.repository.settings import SettingsRepository

        enabled = await SettingsRepository.get_global('BACKUP_ENABLED', False)
        if not enabled:
            logger.info('Авто-бэкап отключён')
            return

        if BackupService._scheduler_task is not None:
            logger.info('Планировщик бэкапов уже запущен')
            return

        BackupService._scheduler_task = asyncio.create_task(
            BackupService._scheduler_loop()
        )
        logger.info('Планировщик авто-бэкапов запущен')

    @staticmethod
    async def _scheduler_loop() -> None:
        """Цикл планировщика: ожидание до времени старта, затем бэкап каждые N часов.

        На каждой итерации перечитывает настройки из базы данных,
        что позволяет изменять параметры без перезапуска.
        """
        from core.repository.settings import SettingsRepository

        first_run = True

        while True:
            try:
                enabled = await SettingsRepository.get_global('BACKUP_ENABLED', False)
                if not enabled:
                    logger.info('Авто-бэкап отключён, планировщик останавливается')
                    return

                if first_run:
                    start_time = await SettingsRepository.get_global('BACKUP_START_TIME', '03:00')

                    try:
                        hour, minute = map(int, str(start_time).split(':'))
                    except (ValueError, AttributeError):
                        hour, minute = 3, 0

                    now = datetime.now()
                    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    if target <= now:
                        target += timedelta(days=1)

                    wait_seconds = (target - now).total_seconds()
                    logger.info(f'Авто-бэкап: первый запуск в {target.strftime("%d.%m.%Y %H:%M")} (ожидание {wait_seconds:.0f}с)')
                    await asyncio.sleep(wait_seconds)
                    first_run = False
                else:
                    interval_hours = await SettingsRepository.get_global('BACKUP_INTERVAL_HOURS', 24)
                    logger.info(f'Авто-бэкап: следующий запуск через {interval_hours}ч')
                    await asyncio.sleep(int(interval_hours) * 3600)

                await BackupService.run_backup()

            except asyncio.CancelledError:
                logger.info('Планировщик бэкапов остановлен')
                return
            except Exception as e:
                logger.error(f'Ошибка в цикле планировщика бэкапов: {e}')
                await asyncio.sleep(60)

    @staticmethod
    async def stop_scheduler() -> None:
        """Останавливает планировщик автоматического резервного копирования."""
        if BackupService._scheduler_task is not None:
            BackupService._scheduler_task.cancel()
            try:
                await BackupService._scheduler_task
            except asyncio.CancelledError:
                pass
            BackupService._scheduler_task = None
            logger.info('Планировщик бэкапов остановлен')
