"""FastAPI приложение веб-панели управления.

Использует общий asyncpg pool с ботом.
"""

import os
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Optional

from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from scalar_fastapi import get_scalar_api_reference, Theme, AgentScalarConfig

from core.config import (
    SECRET_KEY, PANEL_PORT, PERMANENT_SESSION_LIFETIME,
    TESTING, DATABASE_URL, APP_VERSION,
)
from core.logging import logger
from core.sentry import init_sentry, capture_exception

# Пути к статическим ресурсам
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, 'panel', 'static')
TEMPLATES_DIR = os.path.join(BASE_DIR, 'panel', 'templates')

TITLE = 'СТАНКИН Анти-Спам'


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Жизненный цикл приложения: инициализация и очистка ресурсов.

    Алгоритм работы:
        1. Инициализировать пул PostgreSQL, если он ещё не инициализирован.
        2. Инициализировать настройки по умолчанию.
        3. Передать управление приложению.
        4. При завершении закрыть пул, если панель запущена отдельно от бота.

    Аргументы:
        app (FastAPI): Экземпляр приложения FastAPI.
    """
    from core.db import init_pool, close_pool, get_pool
    from core.repository.settings import SettingsRepository

    try:
        get_pool()
        logger.info("Пул PostgreSQL уже инициализирован.")
    except RuntimeError:
        logger.info("Инициализация пула PostgreSQL для панели...")
        await init_pool(DATABASE_URL)
        await SettingsRepository.init_default_global_settings()

    yield

    # Пул закрывается ботом при совместном запуске
    # При отдельном запуске панели — закрываем здесь
    from core.db import _pool
    if _pool is not None:
        # Проверяем, не является ли это частью общего запуска
        # В режиме "только панель" закрываем пул
        import asyncio
        try:
            await close_pool()
        except Exception:
            pass


def create_app() -> FastAPI:
    """Создаёт и настраивает экземпляр FastAPI приложения.

    Возвращаемое значение:
        app (FastAPI): Настроенное приложение с middleware, статикой, шаблонами и роутами.
    """
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY не задан!")

    init_sentry()

    app = FastAPI(
        title=TITLE,
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url='/api/openapi.json',
    )

    @app.get('/docs', include_in_schema=False, response_class=HTMLResponse)
    async def scalar_html(request: Request) -> HTMLResponse:
        """Возвращает страницу Scalar API Reference.

        Доступ только авторизованным пользователям.

        Возвращаемое значение:
            html (HTMLResponse): HTML-страница со Scalar.
        """
        # Проверка авторизации
        user_pk = request.session.get('user_pk')
        if not user_pk:
            return RedirectResponse(url='/login', status_code=303)
        return get_scalar_api_reference(
            openapi_url=app.openapi_url,
            title=f'{TITLE} — API',
            theme=Theme.DEEP_SPACE,
            default_open_all_tags=True,
            expand_all_model_sections=True,
            expand_all_responses=True,
            agent=AgentScalarConfig(disabled=True),
            hide_client_button=True,
            show_developer_tools='never',
            overrides={
                'operationTitleSource': 'summary',
                'externalUrls': {
                    'dashboardUrl': 'https://dashboard.scalar.com',
                    'registryUrl': 'https://registry.scalar.com',
                    'proxyUrl': 'https://proxy.scalar.com',
                    'apiBaseUrl': 'https://api.scalar.com',
                },
                'default': False,
                'isEditable': False,
                'showOperationId': False,
                'defaultOpenFirstTag': True,
                'expandAllSchemaProperties': False,
                'modelsSectionLabel': 'Models',
                'slug': 'api-1',
                'title': 'API #1',
                'showToolbar': 'never',
                'mcp': {
                    'disabled': True,
                },
            },
        )

    # Middleware для сессий
    app.add_middleware(
        SessionMiddleware,
        secret_key=SECRET_KEY,
        max_age=PERMANENT_SESSION_LIFETIME * 60,
        same_site='lax',
    )

    # Статические файлы
    if os.path.exists(STATIC_DIR):
        app.mount('/static', StaticFiles(directory=STATIC_DIR), name='static')

    # Шаблоны
    templates = Jinja2Templates(directory=TEMPLATES_DIR)
    app.state.templates = templates

    # Jinja2 глобальные функции для совместимости с Flask-стилем
    def get_flashed_messages(request: Request) -> list:
        """Возвращает flash-сообщения из сессии и очищает их.

        Аргументы:
            request (Request): Запрос FastAPI.

        Возвращаемое значение:
            messages (list): Список flash-сообщений.
        """
        messages = request.session.pop('_flashes', [])
        return messages

    templates.env.globals['get_flashed_messages'] = get_flashed_messages

    def static_url(path: str) -> str:
        """Добавляет параметр версии к пути статического ресурса.

        Аргументы:
            path (str): Путь к статическому файлу, например /static/styles/main.css.

        Возвращаемое значение:
            url (str): Путь с query-параметром версии, например /static/styles/main.css?v=3.0.0.
        """
        return f"{path}?v={APP_VERSION}"

    templates.env.globals['static_url'] = static_url

    # Регистрация роутов
    from panel.routes.auth import router as auth_router
    from panel.routes.spam import router as spam_router
    from panel.routes.muted import router as muted_router
    from panel.routes.settings import router as settings_router
    from panel.routes.api import router as api_router

    app.include_router(auth_router)
    app.include_router(spam_router)
    app.include_router(muted_router)
    app.include_router(settings_router)
    app.include_router(api_router)

    # Обработчик 404
    from fastapi import HTTPException as _HTTPException
    from starlette.exceptions import HTTPException as _StarletteHTTPException

    @app.exception_handler(_StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: _StarletteHTTPException):
        """Обрабатывает HTTP-исключения и отображает соответствующую страницу ошибки.

        Аргументы:
            request (Request): Запрос FastAPI.
            exc: Перехваченное HTTP-исключение.

        Возвращаемое значение:
            response: HTML-страница с сообщением об ошибке или редирект.
        """
        # Редиректы пропускаем как есть
        if exc.status_code in (301, 302, 303, 307, 308):
            location = exc.headers.get('Location', '/') if exc.headers else '/'
            return RedirectResponse(url=location, status_code=exc.status_code)
        if exc.status_code == 404:
            return templates.TemplateResponse(
                request,
                '404.html',
                {'title': '404 — Страница не найдена', 'active_page': ''},
                status_code=404,
            )
        logger.error(f"HTTP-исключение {exc.status_code}: {exc.detail}")
        if exc.status_code >= 500:
            capture_exception(exc)
        return templates.TemplateResponse(
            request,
            'exception.html',
            {'oops_text': 'Упс! Что-то пошло не так.', 'title': 'Ошибка', 'active_page': ''},
            status_code=exc.status_code,
        )

    # Обработчик неперехваченных исключений
    @app.exception_handler(Exception)
    async def exception_handler(request: Request, exc: Exception) -> HTMLResponse:
        """Обрабатывает неперехваченные исключения и отображает страницу ошибки.

        Аргументы:
            request (Request): Запрос FastAPI.
            exc (Exception): Перехваченное исключение.

        Возвращаемое значение:
            response (HTMLResponse): HTML-страница с сообщением об ошибке.
        """
        logger.error(f"Неперехваченное исключение: {exc}")
        capture_exception(exc)
        return templates.TemplateResponse(
            request,
            'exception.html',
            {'oops_text': 'Упс! Что-то пошло не так.'},
            status_code=500,
        )

    logger.info("FastAPI приложение создано.")
    return app
