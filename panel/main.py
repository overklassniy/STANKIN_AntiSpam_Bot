"""
Основной модуль маршрутов панели управления.
"""

from datetime import datetime, timezone
from typing import Any

from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user

from panel.app import (
    title, icon_path, background_path,
    root_css_path, main_css_path, hamburger_js_path, db
)
from panel.db_models import SpamMessage, MutedUser, Setting, CollectedMessage
from utils.config import HELPDESK_EMAIL, GITHUB_URL
from utils.logging import logger
from utils.helpers import plural_form

main_bp = Blueprint('main', __name__)

# Константы для UI
UI_TEXTS = {
    'about': 'О системе',
    'detected_spam': 'Обнаруженный спам',
    'muted_users': 'Ограниченные пользователи',
    'settings': 'Настройки',
    'logout': 'Выйти',
    'prev': 'Предыдущая',
    'next': 'Следующая',
}

SETTINGS_CSS_PATH = '/static/styles/settings.css'


def get_setting_value(key: str, default=None):
    """Получает значение настройки из БД."""
    setting = Setting.query.get(key)
    if setting:
        return setting.get_typed_value()
    return default


def get_base_context() -> dict:
    """Возвращает базовый контекст для шаблонов."""
    return {
        'root_css_path': root_css_path,
        'main_css_path': main_css_path,
        'hamburger_js_path': hamburger_js_path,
        'icon_path': icon_path,
        'background_path': background_path,
        'og_title': title,
        'title': title,
        'github_url': GITHUB_URL,
        'about_text': UI_TEXTS['about'],
        'detected_spam_text': UI_TEXTS['detected_spam'],
        'muted_users_text': UI_TEXTS['muted_users'],
        'settings_text': UI_TEXTS['settings'],
        'logout_text': UI_TEXTS['logout'],
        'prev_text': UI_TEXTS['prev'],
        'next_text': UI_TEXTS['next'],
    }


def get_pagination_data(query, page: int, per_page: int, endpoint: str) -> dict:
    """
    Генерирует данные пагинации.
    """
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)

    total_pages = paginated.pages
    current_page = paginated.page

    # Диапазон страниц (максимум 5)
    if total_pages <= 5:
        pages = range(1, total_pages + 1)
    elif current_page <= 3:
        pages = range(1, 6)
    elif current_page >= total_pages - 2:
        pages = range(total_pages - 4, total_pages + 1)
    else:
        pages = range(current_page - 2, current_page + 3)

    return {
        'items': paginated.items,
        'total': paginated.total,
        'prev_url': url_for(endpoint, page=paginated.prev_num) if paginated.has_prev else None,
        'next_url': url_for(endpoint, page=paginated.next_num) if paginated.has_next else None,
        'total_pages': total_pages,
        'current_page': current_page,
        'pages': pages,
    }


def format_yes_no(value: Any) -> str:
    """Форматирует значение в Да/Нет/Отключено."""
    if value is None:
        return 'Отключено'
    return 'Да' if value else 'Нет'


def escape_html(text: str) -> str:
    """Экранирует HTML-символы."""
    return (text or '').replace('<', '&lt;').replace('>', '&gt;')


def format_spam_row(item: SpamMessage) -> str:
    """Форматирует строку таблицы спам-сообщений."""
    date = datetime.fromtimestamp(item.timestamp).strftime("%d.%m.%Y<br>%H:%M:%S")

    reply_markup = format_yes_no(item.has_reply_markup)

    if item.cas is None and item.lols is None:
        cas_lols = format_yes_no(None)
    else:
        cas_lols = format_yes_no(bool(item.cas or item.lols))

    chatgpt = format_yes_no(item.chatgpt_prediction)
    message_text = escape_html(item.message_text).replace('\n', '<br>')

    return f"""
        <tr>
            <td class="date">{date}</td>
            <td class="user-id">{item.author_id}</td>
            <td class="username">{item.author_username or '—'}</td>
            <td class="spam_message">{message_text}</td>
            <td class="probability">
                <span class="criteria-item">Имеет inline-клавиатуру: {reply_markup}</span>
                <span class="criteria-item">Забанен CAS / LOLS: {cas_lols}</span>
                <span class="criteria-item">Вердикт ChatGPT: {chatgpt}</span>
                <span class="criteria-item">Вердикт RuBert: {item.bert_prediction}</span>
            </td>
        </tr>
    """


def format_muted_row(item: MutedUser) -> str:
    """Форматирует строку таблицы ограниченных пользователей."""
    date = datetime.fromtimestamp(item.timestamp).strftime("%d.%m.%Y<br>%H:%M:%S")

    if item.muted_till_timestamp:
        try:
            muted_till = datetime.fromtimestamp(
                item.muted_till_timestamp, timezone.utc
            ).strftime("%d.%m.%Y<br>%H:%M:%S")
        except Exception:
            muted_till = datetime.fromtimestamp(
                item.muted_till_timestamp
            ).strftime("%d.%m.%Y<br>%H:%M:%S")
    else:
        muted_till = '—'

    return f"""
        <tr>
            <td class="date">{date}</td>
            <td class="user-id">{item.id}</td>
            <td class="username">{item.username or '—'}</td>
            <td class="date">{muted_till}</td>
            <td class="relapse">{item.relapse_number}</td>
        </tr>
    """


@main_bp.route('/')
@login_required
def index() -> str:
    """Главная страница - список спам-сообщений."""
    logger.info('Запрос главной страницы.')

    per_page = get_setting_value('PER_PAGE', 10)
    page = request.args.get('page', 1, type=int)

    try:
        query = SpamMessage.query.order_by(SpamMessage.timestamp.desc())
        pagination = get_pagination_data(query, page, per_page, 'main.index')

        count = pagination['total']
        rows = ''.join(format_spam_row(item) for item in pagination['items'])

        context = get_base_context()
        context.update({
            'og_description': '',
            'date_text': 'Дата',
            'id_text': 'ID пользователя',
            'username_text': 'Имя пользователя',
            'spam_text': 'Текст сообщения',
            'probability_text': 'Критерии',
            'detected_spam_text_table': (
                f'Обнаруженный спам: {count} '
                f'{plural_form(count, "запись", "записей", "записи")} '
                f'(показываются {per_page})'
            ),
            'rows': rows,
            **{k: pagination[k] for k in ['prev_url', 'next_url', 'total_pages', 'current_page', 'pages']}
        })

        logger.info(f"Страница {pagination['current_page']} из {pagination['total_pages']}")
        return render_template('main.html', **context)

    except Exception as e:
        logger.error(f"Ошибка главной страницы: {e}")
        flash("Ошибка при загрузке данных.", "error")
        return redirect(url_for('auth.login'))


@main_bp.route('/spam')
@login_required
def spam() -> Any:
    """Перенаправление на главную."""
    return redirect(url_for('main.index'))


@main_bp.route('/settings')
@login_required
def settings() -> str:
    """Страница настроек."""
    logger.info("Запрос страницы настроек.")

    try:
        # Получаем все настройки из БД
        all_settings = Setting.query.all()
        fields = []
        for setting in all_settings:
            if setting.value_type == 'bool':
                field_type = 'checkbox'
            elif setting.value_type in ('int', 'float'):
                field_type = 'number'
            else:
                field_type = 'text'

            fields.append({
                'name': setting.key,
                'value': setting.get_typed_value(),
                'type': field_type,
                'description': setting.description or ''
            })

        can_configure = current_user.can_configure

        context = get_base_context()
        context.update({
            'settings_css_path': SETTINGS_CSS_PATH,
            'og_description': UI_TEXTS['about'],
            'fields': fields,
            'can_configure': can_configure,
        })

        return render_template('settings.html', **context)

    except Exception as e:
        logger.error(f"Ошибка страницы настроек: {e}")
        flash("Ошибка при загрузке настроек.", "error")
        return redirect(url_for('main.index'))


@main_bp.route('/settings', methods=['POST'])
@login_required
def settings_post() -> Any:
    """Сохранение настроек."""
    logger.info("POST-запрос настроек.")

    if not current_user.can_configure:
        flash(
            f'У вас нет прав для редактирования конфигурации. Обратитесь в поддержку: '
            f'<a class="animate" href="mailto:{HELPDESK_EMAIL}">{HELPDESK_EMAIL}</a>',
            "error"
        )
        logger.warning(f"Пользователь {current_user.id} без прав на редактирование.")
        return redirect(url_for('main.settings'))

    try:
        # Получаем все настройки из БД
        all_settings = Setting.query.all()

        for setting in all_settings:
            key = setting.key
            old_value = setting.get_typed_value()

            if setting.value_type == 'bool':
                new_value = key in request.form
            elif setting.value_type == 'int':
                try:
                    new_value = int(request.form.get(key, old_value))
                except (ValueError, TypeError):
                    new_value = old_value
            elif setting.value_type == 'float':
                try:
                    new_value = float(request.form.get(key, old_value))
                except (ValueError, TypeError):
                    new_value = old_value
            else:
                new_value = request.form.get(key, old_value)

            # Обновляем значение
            if setting.value_type == 'bool':
                setting.value = 'true' if new_value else 'false'
            else:
                setting.value = str(new_value)

        db.session.commit()
        flash("Настройки сохранены!", "success")
        logger.info("Настройки сохранены в БД.")

    except Exception as e:
        db.session.rollback()
        flash(f"Ошибка сохранения: {e}", "error")
        logger.error(f"Ошибка сохранения настроек: {e}")

    return redirect(url_for('main.settings'))


@main_bp.route('/muted')
@login_required
def muted() -> str:
    """Страница ограниченных пользователей."""
    logger.info('Запрос страницы /muted.')

    per_page = get_setting_value('PER_PAGE', 10)
    page = request.args.get('page', 1, type=int)

    try:
        query = MutedUser.query.order_by(MutedUser.timestamp.desc())
        pagination = get_pagination_data(query, page, per_page, 'main.muted')

        count = pagination['total']
        rows = ''.join(format_muted_row(item) for item in pagination['items'])

        context = get_base_context()
        context.update({
            'og_description': 'Ограниченные пользователи',
            'id_text': 'ID пользователя',
            'username_text': 'Имя пользователя',
            'date_text': 'Дата ограничения',
            'muted_till_text': 'Дата снятия',
            'relapse_number_text': 'Количество нарушений',
            'muted_users_text_table': f'Ограниченных пользователей: {count} (показываются {per_page})',
            'rows': rows,
            **{k: pagination[k] for k in ['prev_url', 'next_url', 'total_pages', 'current_page', 'pages']}
        })

        logger.info(f"Страница {pagination['current_page']} из {pagination['total_pages']}")
        return render_template('muted.html', **context)

    except Exception as e:
        logger.error(f"Ошибка страницы /muted: {e}")
        flash("Ошибка при загрузке данных.", "error")
        return redirect(url_for('main.index'))


@main_bp.route('/collected')
@login_required
def collected() -> str:
    """Страница собранных сообщений."""
    logger.info('Запрос страницы /collected.')

    per_page = get_setting_value('PER_PAGE', 10)
    page = request.args.get('page', 1, type=int)

    try:
        query = CollectedMessage.query.order_by(CollectedMessage.timestamp.desc())
        pagination = get_pagination_data(query, page, per_page, 'main.collected')

        count = pagination['total']
        rows = ""
        for item in pagination['items']:
            date = datetime.fromtimestamp(item.timestamp).strftime("%d.%m.%Y<br>%H:%M:%S")
            message_text = escape_html(item.message_text).replace('\n', '<br>')
            rows += f"""
                <tr>
                    <td class="date">{date}</td>
                    <td class="user-id">{item.user_id}</td>
                    <td class="username">{item.username or '—'}</td>
                    <td class="spam_message">{message_text}</td>
                </tr>
            """

        context = get_base_context()
        context.update({
            'og_description': 'Собранные сообщения',
            'date_text': 'Дата',
            'id_text': 'ID пользователя',
            'username_text': 'Имя пользователя',
            'message_text_header': 'Текст сообщения',
            'collected_text_table': f'Собранных сообщений: {count} (показываются {per_page})',
            'rows': rows,
            **{k: pagination[k] for k in ['prev_url', 'next_url', 'total_pages', 'current_page', 'pages']}
        })

        return render_template('collected.html', **context)

    except Exception as e:
        logger.error(f"Ошибка страницы /collected: {e}")
        flash("Ошибка при загрузке данных.", "error")
        return redirect(url_for('main.index'))
