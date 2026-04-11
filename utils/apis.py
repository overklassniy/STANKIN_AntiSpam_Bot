"""
Модуль для работы с внешними API проверки на спам.

Поддерживаемые API:
- CAS (Combot Anti-Spam): https://cas.chat
- LOLS (List of Lame Spammers): https://lols.bot
"""

from typing import Optional

import aiohttp

from utils.logging import logger

# Таймаут для HTTP-запросов
DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=10)

_shared_session: Optional[aiohttp.ClientSession] = None


async def get_shared_session() -> aiohttp.ClientSession:
    """Возвращает общую aiohttp-сессию, создавая при первом вызове."""
    global _shared_session
    if _shared_session is None or _shared_session.closed:
        _shared_session = aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT)
    return _shared_session


async def close_shared_session() -> None:
    """Закрывает общую aiohttp-сессию (вызывать при остановке бота)."""
    global _shared_session
    if _shared_session and not _shared_session.closed:
        await _shared_session.close()
        _shared_session = None


async def get_cas_async(user_id: int) -> int:
    """
    Асинхронно проверяет пользователя через CAS API.

    CAS (Combot Anti-Spam) - это краудсорсинговая база данных спамеров
    в Telegram, поддерживаемая сообществом.

    Args:
        user_id: Telegram ID пользователя

    Returns:
        1 если пользователь в базе спамеров, 0 если нет или ошибка
    """
    url = f"https://api.cas.chat/check?user_id={user_id}"
    logger.debug(f"CAS проверка пользователя {user_id}")

    try:
        session = await get_shared_session()
        async with session.get(url) as response:
            response.raise_for_status()
            data = await response.json()
            result = int(data.get('ok', 0))
            logger.debug(f"CAS результат для {user_id}: {result}")
            return result
    except aiohttp.ClientError as e:
        logger.error(f"CAS ошибка для {user_id}: {e}")
        return 0
    except Exception as e:
        logger.error(f"CAS неожиданная ошибка для {user_id}: {e}")
        return 0


async def get_lols_async(account_id: int) -> int:
    """
    Асинхронно проверяет пользователя через LOLS API.

    LOLS (List of Lame Spammers) - это база данных известных
    спамеров в Telegram.

    Args:
        account_id: Telegram ID пользователя

    Returns:
        1 если пользователь заблокирован, 0 если нет или ошибка
    """
    url = f"https://api.lols.bot/account?id={account_id}"
    logger.debug(f"LOLS проверка аккаунта {account_id}")

    try:
        session = await get_shared_session()
        async with session.get(url) as response:
            response.raise_for_status()
            data = await response.json()
            result = int(data.get('banned', 0))
            logger.debug(f"LOLS результат для {account_id}: {result}")
            return result
    except aiohttp.ClientError as e:
        logger.error(f"LOLS ошибка для {account_id}: {e}")
        return 0
    except Exception as e:
        logger.error(f"LOLS неожиданная ошибка для {account_id}: {e}")
        return 0


async def check_all_spam_databases(user_id: int) -> dict:
    """
    Проверяет пользователя во всех базах данных спамеров.

    Args:
        user_id: Telegram ID пользователя

    Returns:
        Словарь с результатами проверки
    """
    import asyncio

    cas_task = get_cas_async(user_id)
    lols_task = get_lols_async(user_id)

    cas_result, lols_result = await asyncio.gather(cas_task, lols_task)

    return {
        'cas': bool(cas_result),
        'lols': bool(lols_result),
        'any_banned': bool(cas_result or lols_result)
    }


# Синхронные версии для обратной совместимости (deprecated)
def get_cas(user_id: int) -> int:
    """
    Синхронная проверка CAS.

    DEPRECATED: Используйте get_cas_async для асинхронного кода.
    """
    import requests

    url = f"https://api.cas.chat/check?user_id={user_id}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return int(data.get('ok', 0))
    except Exception as e:
        logger.error(f"CAS sync ошибка для {user_id}: {e}")
        return 0


def get_lols(account_id: int) -> int:
    """
    Синхронная проверка LOLS.

    DEPRECATED: Используйте get_lols_async для асинхронного кода.
    """
    import requests

    url = f"https://api.lols.bot/account?id={account_id}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return int(data.get('banned', 0))
    except Exception as e:
        logger.error(f"LOLS sync ошибка для {account_id}: {e}")
        return 0
