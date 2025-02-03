import json
import os
import sys
from datetime import datetime
from typing import Any

from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user

from panel.app import title, icon_path, background_path, root_css_path
from panel.db_models import SpamMessage

sys.path.append("..")
from utils.basic import config, logger, plural_form
from utils.config_web import prepare_fields

main_bp = Blueprint('main', __name__)

# Пути к статическим ресурсам
main_css_path = '/static/styles/main.css'
settings_css_path = '/static/styles/settings.css'
hamburger_js_path = '/static/scripts/hamburger.js'

about_text = 'О системе'
detected_spam_text = 'Обнаруженный спам'
settings_text = 'Настройки'
logout_text = 'Выйти'

helpdesk_email = os.getenv('helpdesk_email')
github_url = 'https://github.com/overklassniy/STANKIN_AntiSpam_Bot/'


@main_bp.route('/')
@login_required
def index() -> str:
    """
    Формирует главную страницу со списком обнаруженного спама.

    Возвращает:
        str: Сформированное HTML-содержимое страницы.
    """
    logger.info('Обработка запроса главной страницы "/".')

    og_description = ''
    date_text = 'Дата'
    id_text = 'ID пользователя'
    username_text = 'Имя пользователя'
    spam_text = 'Текст сообщения'
    probability_text = 'Критерии'
    prev_text = 'Предыдущая'
    next_text = 'Следующая'

    # Настройки пагинации
    per_page = config['PER_PAGE']  # Количество записей на странице
    page = request.args.get('page', 1, type=int)  # Номер текущей страницы (по умолчанию 1)
    logger.debug("Настроена пагинация: страница %s, записей на странице %s.", page, per_page)

    # Запрос с пагинацией
    detected_spam_list = SpamMessage.query.order_by(SpamMessage.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    logger.info("Получено %s записей спама из базы данных.", detected_spam_list.total)

    count = detected_spam_list.total
    rows = ""
    for item in detected_spam_list.items:
        date = datetime.fromtimestamp(item.timestamp).strftime("%d.%m.%Y<br>%H:%M:%S")
        rows += f"""
                <tr>
                    <td class="date">{date}</td>
                    <td>{item.author_id}</td>
                    <td>{item.author_username or 'N/A'}</td>
                    <td class="spam_message">{item.message_text.replace(chr(10), '<br>')}</td>
                    <td class="probability">
                        Имеет inline-клавиатуру: {item.has_reply_markup}<br>
                        Забанен CAS / LOLS: {max(item.cas, item.lols)}<br>
                        Вердикт ChatGPT: {0 if not item.chatgpt_prediction else item.chatgpt_prediction}<br>
                        Вердикт RuBert: {item.bert_prediction}
                    </td>
                </tr>
            """
    detected_spam_text_table = f'Обнаруженный спам: {count} {plural_form(count, "запись", "записей", "записи")} (показываются {per_page})'
    logger.debug("Сформирована таблица спам-сообщений: %s", detected_spam_text_table)

    # Навигация по страницам
    prev_url = url_for('main.index', page=detected_spam_list.prev_num) if detected_spam_list.has_prev else None
    next_url = url_for('main.index', page=detected_spam_list.next_num) if detected_spam_list.has_next else None
    total_pages = detected_spam_list.pages  # Общее количество страниц
    current_page = detected_spam_list.page  # Текущая страница

    logger.info("Пагинация: страница %s из %s.", current_page, total_pages)

    rendered_page = render_template(
        'main.html',
        root_css_path=root_css_path,
        main_css_path=main_css_path,
        hamburger_js_path=hamburger_js_path,

        icon_path=icon_path,
        background_path=background_path,

        og_title=title,
        og_description=og_description,
        title=title,
        github_url=github_url,
        about_text=about_text,
        detected_spam_text=detected_spam_text,
        settings_text=settings_text,
        logout_text=logout_text,
        detected_spam_text_table=detected_spam_text_table,
        date_text=date_text,
        id_text=id_text,
        username_text=username_text,
        spam_text=spam_text,
        probability_text=probability_text,
        rows=rows,
        prev_url=prev_url,
        prev_text=prev_text,
        next_url=next_url,
        next_text=next_text,
        total_pages=total_pages,
        current_page=current_page
    )
    logger.info("Главная страница успешно сформирована.")
    return rendered_page


@main_bp.route('/spam')
@login_required
def spam() -> Any:
    """
    Перенаправляет пользователя на главную страницу.
    """
    logger.info("Запрос '/spam' перенаправляется на главную страницу.")
    return redirect(url_for('main.index'))


@main_bp.route('/settings')
@login_required
def settings() -> str:
    """
    Формирует страницу настроек.

    Возвращает:
        str: Сформированное HTML-содержимое страницы настроек.
    """
    logger.info("Обработка запроса страницы настроек '/settings'.")
    fields = prepare_fields(config)
    can_configure = current_user.can_configure
    logger.debug("Права пользователя на изменение настроек: %s", can_configure)

    rendered_page = render_template(
        'settings.html',

        root_css_path=root_css_path,
        main_css_path=main_css_path,
        settings_css_path=settings_css_path,

        hamburger_js_path=hamburger_js_path,

        icon_path=icon_path,
        background_path=background_path,

        og_title=title,
        og_description=about_text,
        title=title,
        github_url=github_url,
        about_text=about_text,
        detected_spam_text=detected_spam_text,
        settings_text=settings_text,
        logout_text=logout_text,
        fields=fields,
        can_configure=can_configure
    )
    logger.info("Страница настроек успешно сформирована.")
    return rendered_page


@main_bp.route('/settings', methods=['POST'])
@login_required
def settings_post() -> Any:
    """
    Обрабатывает POST-запрос для сохранения настроек. Получает данные из формы, обновляет конфигурацию и сохраняет её в файл config.json.
    """
    logger.info("Получен POST-запрос для обновления настроек.")
    can_configure = current_user.can_configure
    if can_configure:
        # Создаем новый словарь для обновленной конфигурации
        new_config = {}

        # Обновляем значения конфигурации из данных формы
        for key, value in config.items():
            if isinstance(value, bool):
                new_config[key] = key in request.form
                logger.debug("Обновлена булевая настройка '%s': %s", key, new_config[key])
            elif isinstance(value, int):
                form_value = request.form.get(key, None)
                try:
                    new_config[key] = int(form_value) if form_value is not None else value
                    logger.debug("Обновлена целочисленная настройка '%s': %s", key, new_config[key])
                except ValueError:
                    new_config[key] = value
                    logger.warning("Неверное значение для настройки '%s'. Использовано значение по умолчанию.", key)
            elif isinstance(value, float):
                form_value = request.form.get(key, None)
                try:
                    new_config[key] = float(form_value) if form_value is not None else value
                    logger.debug("Обновлена настройка с плавающей точкой '%s': %s", key, new_config[key])
                except ValueError:
                    new_config[key] = value
                    logger.warning("Неверное значение для настройки '%s'. Использовано значение по умолчанию.", key)
            else:
                new_config[key] = request.form.get(key, value)
                logger.debug("Обновлена строковая настройка '%s': %s", key, new_config[key])

        config_path = 'config.json'
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(new_config, f, indent=4, ensure_ascii=False)
            flash("Настройки успешно сохранены! Пожалуйста, перезагрузите систему.", "success")
            logger.info("Конфигурация успешно сохранена в файл '%s'.", config_path)
        except Exception as e:
            flash(f"Ошибка при сохранении настроек: {str(e)}", "error")
            logger.error("Ошибка при сохранении настроек в файл '%s': %s", config_path, e)

        # Обновляем глобальный объект config
        config.clear()
        config.update(new_config)
        logger.info("Глобальный объект конфигурации обновлен.")
    else:
        flash(
            f'Вы не можете редактировать конфигурацию системы. Пожалуйста, обратитесь в техническую поддержку по адресу '
            f'<a class="animate" href="mailto:{helpdesk_email}">{helpdesk_email}</a> для получения полномочий.',
            "error"
        )
        logger.warning("Пользователь %s не имеет прав для редактирования настроек.", current_user.id)

    logger.info("Перенаправление пользователя обратно на страницу настроек.")
    return redirect(url_for('main.settings'))
