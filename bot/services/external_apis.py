"""Сервис проверки пользователей через внешние API.

Поддерживаемые API:
- CAS (Combot Anti-Spam): https://cas.chat
- LOLS (List of Lame Spammers): https://lols.bot
"""

from typing import Optional

import aiohttp

from core.logging import logger

DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=10)

_shared_session: Optional[aiohttp.ClientSession] = None


async def get_shared_session() -> aiohttp.ClientSession:
    """Возвращает общую aiohttp-сессию, создавая при первом вызове.

    Возвращаемое значение:
        session (aiohttp.ClientSession): Общая HTTP-сессия.
    """
    global _shared_session
    if _shared_session is None or _shared_session.closed:
        _shared_session = aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT)
    return _shared_session


async def close_shared_session() -> None:
    """Закрывает общую aiohttp-сессию.

    Вызывать при остановке бота.
    """
    global _shared_session
    if _shared_session and not _shared_session.closed:
        await _shared_session.close()
        _shared_session = None


async def check_cas(user_id: int) -> bool:
    """Проверяет пользователя через CAS API.

    CAS (Combot Anti-Spam) — краудсорсинговая база данных спамеров
    в Telegram, поддерживаемая сообществом.

    Аргументы:
        user_id (int): Telegram ID пользователя.

    Возвращаемое значение:
        bool: True если пользователь в базе спамеров.
    """
    url = f"https://api.cas.chat/check?user_id={user_id}"
    logger.debug(f"CAS проверка пользователя {user_id}")

    try:
        session = await get_shared_session()
        async with session.get(url) as response:
            response.raise_for_status()
            data = await response.json()
            result = bool(data.get('ok', 0))
            logger.debug(f"CAS результат для {user_id}: {result}")
            return result
    except aiohttp.ClientError as e:
        logger.error(f"CAS ошибка для {user_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"CAS неожиданная ошибка для {user_id}: {e}")
        return False


async def check_lols(account_id: int) -> bool:
    """Проверяет пользователя через LOLS API.

    LOLS (List of Lame Spammers) — база данных известных
    спамеров в Telegram.

    Аргументы:
        account_id (int): Telegram ID пользователя.

    Возвращаемое значение:
        bool: True если пользователь заблокирован.
    """
    url = f"https://api.lols.bot/account?id={account_id}"
    logger.debug(f"LOLS проверка аккаунта {account_id}")

    try:
        session = await get_shared_session()
        async with session.get(url) as response:
            response.raise_for_status()
            data = await response.json()
            result = bool(data.get('banned', 0))
            logger.debug(f"LOLS результат для {account_id}: {result}")
            return result
    except aiohttp.ClientError as e:
        logger.error(f"LOLS ошибка для {account_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"LOLS неожиданная ошибка для {account_id}: {e}")
        return False


async def check_all_spam_databases(user_id: int) -> dict:
    """Проверяет пользователя во всех базах данных спамеров.

    Аргументы:
        user_id (int): Telegram ID пользователя.

    Возвращаемое значение:
        dict: Словарь с результатами проверки (cas, lols, any_banned).
    """
    import asyncio

    cas_task = check_cas(user_id)
    lols_task = check_lols(user_id)

    cas_result, lols_result = await asyncio.gather(cas_task, lols_task)

    return {
        'cas': cas_result,
        'lols': lols_result,
        'any_banned': cas_result or lols_result
    }
