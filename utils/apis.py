from typing import Union

import requests

from utils.basic import logger


def get_cas(user_id: int) -> Union[int, dict]:
    """
    Получает JSON-ответ от API https://api.cas.chat/check.

    Аргументы:
        user_id (int): ID пользователя, который нужно проверить.

    Возвращает:
        int | dict: Целочисленный результат проверки CAS. При ошибке возвращается 0.
    """
    url = f"https://api.cas.chat/check?user_id={user_id}"
    logger.info("Начало проверки CAS для пользователя с ID: %s", user_id)
    try:
        response = requests.get(url)
        response.raise_for_status()  # Проверяем наличие ошибок HTTP
        data = response.json()
        logger.debug("Получен ответ от CAS API для пользователя %s: %s", user_id, data)
        result = int(data.get('ok', 0))
        logger.info("Проверка CAS завершена успешно для пользователя %s, результат: %s", user_id, result)
        return result
    except requests.exceptions.RequestException as e:
        logger.error("Ошибка при проверке CAS для пользователя %s: %s", user_id, e)
        return 0


def get_lols(account_id: int) -> Union[int, dict]:
    """
    Получает JSON-ответ от API https://api.lols.bot/account.

    Аргументы:
        account_id (int): ID аккаунта, который нужно проверить.

    Возвращает:
        int | dict: Целочисленный результат проверки LOLS. При ошибке возвращается 0.
    """
    url = f"https://api.lols.bot/account?id={account_id}"
    logger.info("Начало проверки LOLS для аккаунта с ID: %s", account_id)
    try:
        response = requests.get(url)
        response.raise_for_status()  # Проверяем наличие ошибок HTTP
        data = response.json()
        logger.debug("Получен ответ от LOLS API для аккаунта %s: %s", account_id, data)
        result = int(data.get('banned', 0))
        logger.info("Проверка LOLS завершена успешно для аккаунта %s, результат: %s", account_id, result)
        return result
    except requests.exceptions.RequestException as e:
        logger.error("Ошибка при проверке LOLS для аккаунта %s: %s", account_id, e)
        return 0
