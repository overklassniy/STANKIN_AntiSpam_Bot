"""Маршруты для просмотра ограниченных пользователей."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Request, Query, Depends
from fastapi.responses import HTMLResponse

from core.repository.muted import MutedRepository
from core.repository.settings import SettingsRepository
from core.repository.user import UserRepository
from panel.routes.auth import require_user
from core.utils import plural_form, escape_html, get_visible_pages
from core.logging import logger

router = APIRouter()


def format_muted_row(item: dict) -> str:
    """Форматирует строку таблицы ограниченных пользователей.

    Аргументы:
        item (dict): Запись ограниченного пользователя.

    Возвращаемое значение:
        html (str): HTML-строка таблицы.
    """
    date = datetime.fromtimestamp(item['timestamp']).strftime("%d.%m.%Y<br>%H:%M:%S")

    if item.get('muted_till_timestamp'):
        muted_till = datetime.fromtimestamp(item['muted_till_timestamp']).strftime("%d.%m.%Y %H:%M:%S")
    else:
        muted_till = '—'

    return f"""
        <tr>
            <td class="date">{date}</td>
            <td class="user-id">{item['user_id']}</td>
            <td class="username">{item.get('username') or '—'}</td>
            <td class="muted-till">{muted_till}</td>
            <td class="relapse">{item['relapse_number']}</td>
        </tr>
    """


@router.get('/muted', response_class=HTMLResponse)
async def muted_page(
    request: Request,
    page: int = Query(1, ge=1),
    user: dict = Depends(require_user),
):
    """# Страница ограниченных пользователей

    Отображает HTML-страницу с таблицей ограниченных пользователей и пагинацией.

    ## Когда использовать

    Используйте этот эндпоинт для отображения страницы со списком ограниченных пользователей.

    ## Требуемые права

    Запрос доступен только авторизованному пользователю.

    ## Пагинация

    Список возвращается постранично. Параметр `page` задаёт номер страницы, начиная с 1. Количество записей на странице определяется глобальной настройкой `PER_PAGE`.

    ## Успешный ответ

    Возвращает HTML-страницу с таблицей и навигацией по страницам.

    ## Особенности

    * Суперпользователь видит записи из всех чатов.
    * Обычный пользователь видит записи только из доступных ему чатов.

    Аргументы:
        request (Request): Запрос FastAPI.
        page (int): Номер страницы, начиная с 1.
        user (dict): Данные текущего пользователя.
    """
    logger.info('Запрос страницы ограниченных пользователей.')

    per_page = await SettingsRepository.get_global('PER_PAGE', 10)

    chat_pks = None
    if not user['is_superadmin']:
        chat_pks = await UserRepository.get_accessible_chat_pks(user['id'])

    pagination = await MutedRepository.get_muted_users(
        chat_pks=chat_pks, page=page, per_page=per_page
    )

    count = pagination['total']
    rows = ''.join(format_muted_row(item) for item in pagination['items'])

    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        'muted.html',
        {
            'title': 'Ограниченные пользователи',
            'og_title': 'Ограниченные пользователи',
            'og_description': '',
            'active_page': 'muted',
            'github_url': 'https://github.com/overklassniy/STANKIN_AntiSpam_Bot/',
            'muted_users_text_table': (
                f'Ограниченные пользователи: {count} '
                f'{plural_form(count, "запись", "записей", "записи")} '
                f'(показывается {per_page})'
            ),
            'rows': rows,
            'prev_url': f'/muted?page={pagination["current_page"] - 1}' if pagination['current_page'] > 1 else None,
            'next_url': f'/muted?page={pagination["current_page"] + 1}' if pagination['current_page'] < pagination['total_pages'] else None,
            'total_pages': pagination['total_pages'],
            'current_page': pagination['current_page'],
            'pages': get_visible_pages(pagination['current_page'], pagination['total_pages']),
        }
    )
