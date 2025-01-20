from typing import Union

import requests


def get_cas(user_id: int) -> Union[int, dict]:
    """
    Получает JSON-ответ от API https://api.cas.chat/check.

    Параметры:
        user_id (int): ID пользователя, который нужно проверить.

    Возвращает:
        int | dict: JSON-ответ от API или сообщение об ошибке.
    """
    url = f"https://api.cas.chat/check?user_id={user_id}"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Проверяем наличие ошибок HTTP
        return int(response.json()['ok'])
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def get_lols(account_id: int) -> Union[int, dict]:
    """
    Получает JSON-ответ от API https://api.lols.bot/account.

    Параметры:
        account_id (str): ID аккаунта, который нужно проверить.

    Возвращает:
        int | dict: JSON-ответ от API или сообщение об ошибке.
    """
    url = f"https://api.lols.bot/account?id={account_id}"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Проверяем наличие ошибок HTTP
        return int(response.json()['banned'])
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}
