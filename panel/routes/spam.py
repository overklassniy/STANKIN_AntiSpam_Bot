"""Маршруты для просмотра спам-сообщений.

Доступ фильтруется по чатам, доступным пользователю.
"""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Request, Query, Depends
from fastapi.responses import HTMLResponse
from starlette.responses import RedirectResponse

from core.repository.spam import SpamRepository
from core.repository.user import UserRepository
from core.repository.settings import SettingsRepository
from panel.routes.auth import require_user
from core.utils import plural_form, escape_html
from core.logging import logger

router = APIRouter()


def format_yes_no(value) -> str:
    """Форматирует значение в строку Да / Нет / Отключено.

    Аргументы:
        value: Значение для форматирования.

    Возвращаемое значение:
        text (str): Строка Да, Нет или Отключено.
    """
    if value is None:
        return 'Отключено'
    return 'Да' if value else 'Нет'


def format_spam_row(item: dict) -> str:
    """Форматирует строку таблицы спам-сообщений.

    Аргументы:
        item (dict): Запись спам-сообщения.

    Возвращаемое значение:
        html (str): HTML-строка таблицы.
    """
    date = datetime.fromtimestamp(item['timestamp']).strftime("%d.%m.%Y<br>%H:%M:%S")

    reply_markup = format_yes_no(item.get('has_reply_markup'))

    if item.get('cas') is None and item.get('lols') is None:
        cas_lols = format_yes_no(None)
    else:
        cas_lols = format_yes_no(bool(item.get('cas') or item.get('lols')))

    chatgpt = format_yes_no(item.get('chatgpt_prediction'))
    message_text = escape_html(item['message_text']).replace('\n', '<br>')

    bert_val = item.get('bert_prediction')
    if bert_val is None:
        bert_str = 'Отключено'
    else:
        bert_str = f'{bert_val}'

    return f"""
        <tr>
            <td class="date">{date}</td>
            <td class="user-id">{item['author_id']}</td>
            <td class="username">{item.get('author_username') or '—'}</td>
            <td class="spam_message">{message_text}</td>
            <td class="probability">
                <span class="criteria-item">Имеет inline-клавиатуру: {reply_markup}</span>
                <span class="criteria-item">Забанен CAS / LOLS: {cas_lols}</span>
                <span class="criteria-item">Вердикт ChatGPT: {chatgpt}</span>
                <span class="criteria-item">Вердикт RuBert: {bert_str}</span>
            </td>
        </tr>
    """


@router.get('/', response_class=HTMLResponse)
async def index(
    request: Request,
    page: int = Query(1, ge=1),
    user: dict = Depends(require_user),
):
    """# Главная страница — список спам-сообщений

    Отображает HTML-страницу с таблицей обнаруженных спам-сообщений и пагинацией.

    ## Когда использовать

    Используйте этот эндпоинт для отображения главной страницы веб-панели со списком обнаруженного спама.

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
    logger.info('Запрос главной страницы.')

    per_page = await SettingsRepository.get_global('PER_PAGE', 10)

    # Получаем доступные чаты
    if user['is_superadmin']:
        chat_pks = None
    else:
        chat_pks = await UserRepository.get_accessible_chat_pks(user['id'])

    pagination = await SpamRepository.get_spam_messages(
        chat_pks=chat_pks, page=page, per_page=per_page
    )

    count = pagination['total']
    rows = ''.join(format_spam_row(item) for item in pagination['items'])

    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        'main.html',
        {
            'title': 'СТАНКИН Анти-Спам',
            'og_title': 'СТАНКИН Анти-Спам',
            'og_description': '',
            'active_page': 'spam',
            'github_url': 'https://github.com/overklassniy/STANKIN_AntiSpam_Bot/',
            'detected_spam_text_table': (
                f'Обнаруженный спам: {count} '
                f'{plural_form(count, "запись", "записей", "записи")} '
                f'(показывается {per_page})'
            ),
            'rows': rows,
            'prev_url': f'/?page={pagination["current_page"] - 1}' if pagination['current_page'] > 1 else None,
            'next_url': f'/?page={pagination["current_page"] + 1}' if pagination['current_page'] < pagination['total_pages'] else None,
            'total_pages': pagination['total_pages'],
            'current_page': pagination['current_page'],
            'pages': range(1, pagination['total_pages'] + 1),
        }
    )
