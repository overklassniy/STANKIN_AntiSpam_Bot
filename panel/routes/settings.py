"""Маршруты для управления настройками.

Глобальные настройки доступны только суперпользователю.
Per-chat настройки доступны админам соответствующих чатов.
"""

import os
from typing import Any, Dict, List

from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse
from starlette.responses import RedirectResponse

from core.repository.settings import SettingsRepository, SETTING_DESCRIPTIONS
from core.repository.chat import ChatRepository
from core.repository.user import UserRepository
from panel.routes.auth import require_user
from core.config import DEFAULT_SETTINGS, MODELS_DIR
from core.logging import logger

router = APIRouter()


def _get_available_bert_models() -> List[str]:
    """Возвращает список доступных BERT-моделей из директории models.

    Возвращаемое значение:
        List[str]: Список имён поддиректорий, содержащих файл config.json.
    """
    models: List[str] = []
    if not os.path.isdir(MODELS_DIR):
        return models
    for name in os.listdir(MODELS_DIR):
        path = os.path.join(MODELS_DIR, name)
        if os.path.isdir(path) and os.path.isfile(os.path.join(path, 'config.json')):
            models.append(name)
    models.sort()
    return models


@router.get('/settings', response_class=HTMLResponse)
async def settings_page(
    request: Request,
    user: dict = Depends(require_user),
):
    """# Страница настроек системы

    Отображает HTML-страницу с формой редактирования настроек системы.

    ## Когда использовать

    Используйте этот эндпоинт для отображения страницы настроек в веб-панели.

    ## Требуемые права

    Запрос доступен только авторизованному пользователю. Суперпользователь видит глобальные настройки и все чаты. Обычный пользователь видит только настройки чатов, которые ему назначены.

    ## Успешный ответ

    Возвращает HTML-страницу с формой настроек.

    Аргументы:
        request (Request): Запрос FastAPI.
        user (dict): Данные текущего пользователя.
    """
    logger.info('Запрос страницы настроек.')

    global_settings = {}
    chats = []

    if user['is_superadmin']:
        global_settings = await SettingsRepository.get_all_global()
        if not global_settings:
            await SettingsRepository.init_default_global_settings()
            global_settings = await SettingsRepository.get_all_global()
        chats = await ChatRepository.get_active_chats()
    else:
        accessible = await UserRepository.get_user_chats(user['id'])
        chats = accessible

    # Преобразуем настройки в список полей для шаблона (только для суперпользователя)
    bert_models = _get_available_bert_models()
    fields = []
    if user['is_superadmin']:
        for key in DEFAULT_SETTINGS:
            value = global_settings.get(key, DEFAULT_SETTINGS[key])
            if key == 'BERT_MODEL':
                field_type = 'select'
            elif isinstance(value, bool):
                field_type = 'checkbox'
            elif isinstance(value, (int, float)):
                field_type = 'number'
            else:
                field_type = 'text'
            field = {
                'name': key,
                'value': value,
                'type': field_type,
                'description': SETTING_DESCRIPTIONS.get(key, ''),
            }
            if field_type == 'select':
                field['options'] = bert_models
            fields.append(field)

    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        'settings.html',
        {
            'title': 'Настройки',
            'og_title': 'Настройки',
            'og_description': '',
            'active_page': 'settings',
            'github_url': 'https://github.com/overklassniy/STANKIN_AntiSpam_Bot/',
            'global_settings': global_settings,
            'chats': chats,
            'is_superadmin': user['is_superadmin'],
            'can_configure': user['is_superadmin'],
            'fields': fields,
            'bert_models': bert_models,
        }
    )


@router.post('/settings/global')
async def update_global_settings(
    request: Request,
    user: dict = Depends(require_user),
):
    """# Обновление глобальных настроек

    Сохраняет значения глобальных настроек системы из формы.

    ## Когда использовать

    Используйте этот эндпоинт при отправке формы редактирования глобальных настроек на странице `/settings`.

    ## Требуемые права

    Запрос доступен только суперпользователю.

    ## Успешный ответ

    Редирект 303 на `/settings`.

    ## Побочные эффекты

    * Изменения вступают в силу немедленно и влияют на все чаты.

    Аргументы:
        request (Request): Запрос FastAPI.
        user (dict): Данные текущего пользователя.
    """
    if not user['is_superadmin']:
        return RedirectResponse(url='/settings', status_code=303)

    form = await request.form()

    for key, value in form.items():
        if key in ('save',):
            continue

        # Определяем тип и преобразуем
        if value.lower() in ('true', 'false'):
            parsed = value.lower() == 'true'
        elif value.replace('.', '', 1).isdigit():
            parsed = float(value) if '.' in value else int(value)
        else:
            parsed = value

        await SettingsRepository.update_global(key, parsed)
        logger.info(f"Глобальная настройка '{key}' обновлена: {parsed}")

    return RedirectResponse(url='/settings', status_code=303)


@router.post('/settings/chat/{chat_pk}')
async def update_chat_settings(
    request: Request,
    chat_pk: int,
    user: dict = Depends(require_user),
):
    """# Обновление настроек чата

    Сохраняет значения настроек конкретного чата из формы.

    ## Когда использовать

    Используйте этот эндпоинт при отправке формы редактирования настроек чата на странице `/settings`.

    ## Требуемые права

    Запрос доступен только авторизованному пользователю. Суперпользователь имеет доступ ко всем чатам. Обычный пользователь имеет доступ только к чатам, которые ему назначены.

    ## Успешный ответ

    Редирект 303 на `/settings`.

    ## Побочные эффекты

    * Изменения вступают в силу немедленно и влияют только на указанный чат.

    Аргументы:
        request (Request): Запрос FastAPI.
        chat_pk (int): PK чата.
        user (dict): Данные текущего пользователя.
    """
    # Проверка доступа
    if not user['is_superadmin']:
        accessible = await UserRepository.get_accessible_chat_pks(user['id'])
        if chat_pk not in accessible:
            return RedirectResponse(url='/settings', status_code=303)

    form = await request.form()

    for key, value in form.items():
        if key in ('save',):
            continue

        if value.lower() in ('true', 'false'):
            parsed = value.lower() == 'true'
        elif value.replace('.', '', 1).isdigit():
            parsed = float(value) if '.' in value else int(value)
        else:
            parsed = value

        await SettingsRepository.update_chat_setting(chat_pk, key, parsed)
        logger.info(f"Настройка чата {chat_pk} '{key}' обновлена: {parsed}")

    return RedirectResponse(url='/settings', status_code=303)
