"""Аутентификация для веб-панели.

Session-based auth с проверкой доступа к чатам.
"""

import hashlib
import os
from typing import Optional

from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse
from starlette.responses import RedirectResponse
from starlette.requests import Request as StarletteRequest

from core.repository.user import UserRepository
from core.logging import logger


def _get_bot_username() -> str:
    """Возвращает имя бота из глобальной переменной bot.core.

    Возвращаемое значение:
        username (str): Имя бота без @, или пустая строка, если бот не запущен.
    """
    try:
        from bot.core import bot_username
        return bot_username or ''
    except Exception:
        return ''

router = APIRouter()

TITLE = 'СТАНКИН Анти-Спам'


def verify_password(password: str, stored_hash: str) -> bool:
    """Проверяет пароль против хеша.

    Поддерживает три формата хеша:
    * scrypt — собственный формат `scrypt$параметры$salt$hash`;
    * werkzeug scrypt — формат `scrypt:N:r:p$salt$hash` (без зависимости werkzeug);
    * werkzeug — устаревший формат из предыдущей версии (через werkzeug, если установлен).

    Аргументы:
        password (str): Введённый пароль.
        stored_hash (str): Хранящийся хеш.

    Возвращаемое значение:
        ok (bool): True, если пароль совпадает с хешем.
    """
    if stored_hash.startswith('scrypt$'):
        # Формат: scrypt${n=...,r=...,p=...}${salt}${hash}
        try:
            parts = stored_hash.split('$')
            params_str = parts[1]
            salt = bytes.fromhex(parts[2])
            expected_hash = parts[3]

            params = {}
            for p in params_str.split(','):
                k, v = p.split('=')
                params[k] = int(v)

            dk = hashlib.scrypt(
                password.encode(),
                salt=salt,
                n=params.get('n', 16384),
                r=params.get('r', 8),
                p=params.get('p', 1),
                dklen=64
            )
            return dk.hex() == expected_hash
        except Exception:
            return False

    if stored_hash.startswith('scrypt:'):
        # Формат werkzeug: scrypt:N:r:p$salt$hash
        try:
            method, salt_hash = stored_hash.split('$', 1)
            salt_b64, expected_hash = salt_hash.split('$', 1)
            _, n, r, p = method.split(':')
            n, r, p = int(n), int(r), int(p)

            import base64
            salt = base64.b64decode(salt_b64)
            dk = hashlib.scrypt(
                password.encode(),
                salt=salt,
                n=n,
                r=r,
                p=p,
                dklen=64
            )
            return base64.b64encode(dk).decode() == expected_hash
        except Exception:
            return False

    # Совместимость с другими устаревшими форматами werkzeug
    try:
        from werkzeug.security import check_password_hash
        return check_password_hash(stored_hash, password)
    except Exception:
        return False


def get_current_user(request: Request) -> Optional[dict]:
    """Получает текущего пользователя из сессии.

    Аргументы:
        request (Request): Запрос FastAPI.

    Возвращаемое значение:
        user (Optional[dict]): Данные пользователя или None, если сессия отсутствует.
    """
    user_pk = request.session.get('user_pk')
    if not user_pk:
        return None

    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return None
        user = loop.run_until_complete(UserRepository.get_user_by_id(user_pk))
        return user
    except RuntimeError:
        # Event loop уже запущен — используем синхронную версию
        return _get_user_sync(user_pk)


def _get_user_sync(user_pk: int) -> Optional[dict]:
    """Синхронное получение пользователя (fallback).

    Аргументы:
        user_pk (int): PK пользователя.

    Возвращаемое значение:
        user (Optional[dict]): Данные пользователя или None.
    """
    import asyncio
    try:
        loop = asyncio.new_event_loop()
        user = loop.run_until_complete(UserRepository.get_user_by_id(user_pk))
        loop.close()
        return user
    except Exception:
        return None


async def require_user(request: Request) -> dict:
    """Зависимость для проверки аутентификации страниц.

    Аргументы:
        request (Request): Запрос FastAPI.

    Возвращаемое значение:
        user (dict): Данные пользователя.

    Исключения:
        HTTPException: 303 редирект на /login, если не аутентифицирован.
    """
    user_pk = request.session.get('user_pk')
    if not user_pk:
        raise HTTPException(status_code=303, headers={'Location': '/login'})

    user = await UserRepository.get_user_by_id(user_pk)
    if not user:
        request.session.clear()
        raise HTTPException(status_code=303, headers={'Location': '/login'})

    return user


def _redirect_to_login() -> RedirectResponse:
    """Возвращает редирект на страницу входа.

    Возвращаемое значение:
        response (RedirectResponse): Редирект 303 на /login.
    """
    return RedirectResponse(url='/login', status_code=303)


async def require_user_api(request: Request) -> dict:
    """Зависимость для проверки аутентификации в REST API.

    Аргументы:
        request (Request): Запрос FastAPI.

    Возвращаемое значение:
        user (dict): Данные пользователя.

    Исключения:
        HTTPException: 401, если не аутентифицирован.
    """
    from fastapi import HTTPException

    user_pk = request.session.get('user_pk')
    if not user_pk:
        raise HTTPException(status_code=401, detail='Не авторизован')

    user = await UserRepository.get_user_by_id(user_pk)
    if not user:
        request.session.clear()
        raise HTTPException(status_code=401, detail='Пользователь не найден')

    return user


@router.get('/login', response_class=HTMLResponse)
async def login_page(request: Request, error: Optional[str] = None):
    """# Страница входа в систему

    Отображает HTML-страницу с формой входа. При наличии параметра `error` показывает сообщение об ошибке.

    ## Когда использовать

    Используйте этот эндпоинт для отображения страницы входа пользователю, который ещё не авторизован.

    ## Успешный ответ

    Возвращает HTML-страницу с формой входа.

    Аргументы:
        request (Request): Запрос FastAPI.
        error (Optional[str]): Флаг ошибки аутентификации.
    """
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        'login.html',
        {
            'title': TITLE,
            'og_title': TITLE,
            'og_description': 'Вход в систему',
            'bot_name': _get_bot_username(),
            'login_error': error is not None,
        }
    )


@router.post('/login')
async def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    remember: Optional[str] = Form(None),
):
    """# Обработка входа в систему

    Проверяет учётные данные пользователя и создаёт сессию. При успешном входе выполняет редирект на главную страницу.

    ## Когда использовать

    Используйте этот эндпоинт при отправке формы входа на странице `/login`.

    ## Параметры запроса

    | Поле | Тип | Обязательное | Описание |
    | --- | --- | --- | --- |
    | username | string | Да | Имя пользователя. |
    | password | string | Да | Пароль пользователя. |
    | remember | string | Нет | Флаг продления сессии. |

    ## Успешный ответ

    Редирект 303 на главную страницу `/`.

    ## Возможные ошибки

    При неверных учётных данных выполняется редирект 303 на `/login?error=1`.

    ## Особенности

    * Имя пользователя обрезается от пробельных символов перед проверкой.
    * Сессия хранится в cookie.

    Аргументы:
        request (Request): Запрос FastAPI.
        username (str): Имя пользователя из формы.
        password (str): Пароль из формы.
        remember (Optional[str]): Флаг продления сессии.
    """
    logger.info(f"Попытка входа: '{username}'")

    user = await UserRepository.get_user_by_name(username.strip())

    if not user or not user.get('password_hash'):
        logger.warning(f"Неудачная попытка входа: '{username}'")
        return RedirectResponse(url='/login?error=1', status_code=303)

    if not verify_password(password, user['password_hash']):
        logger.warning(f"Неудачная попытка входа: '{username}'")
        return RedirectResponse(url='/login?error=1', status_code=303)

    request.session['user_pk'] = user['id']
    logger.info(f"Пользователь '{username}' вошёл в систему.")
    return RedirectResponse(url='/', status_code=303)


@router.get('/logout')
async def logout(request: Request):
    """# Выход из системы

    Завершает сессию пользователя и выполняет редирект на страницу входа.

    ## Когда использовать

    Используйте этот эндпоинт, когда пользователь нажимает кнопку выхода из системы.

    ## Что происходит

    После успешного выполнения запроса:

    * сессия пользователя очищается;
    * выполняется редирект на страницу входа.

    ## Успешный ответ

    Редирект 303 на `/login`.

    Аргументы:
        request (Request): Запрос FastAPI.
    """
    user_pk = request.session.get('user_pk')
    request.session.clear()
    if user_pk:
        logger.info(f"Пользователь {user_pk} вышел из системы.")
    return RedirectResponse(url='/login', status_code=303)
