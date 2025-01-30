import sys
from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, request
from flask_login import login_required

from panel.app import title, icon_path, background_path, root_css_path
from panel.db_models import SpamMessage

sys.path.append("../utils")
from basic import load_json_file, config, plural_form

main_bp = Blueprint('main', __name__)


# Пути к статическим ресурсам
main_css_path = '/static/styles/main.css'

hamburger_js_path = '/static/scripts/hamburger.js'

about_text = 'О системе'
detected_spam_text = 'Обнаруженный спам'
settings_text = 'Настройки'
logout_text = 'Выйти'


@main_bp.route('/')
@login_required
def index():
    og_description = ''
    date_text = 'Дата'
    id_text = 'ID пользователя'
    username_text = 'Имя пользователя'
    spam_text = 'Текст сообщения'
    probability_text = 'Критерии'
    prev_text = 'Предыдущая'
    next_text = 'Следующая'

    # Настройки пагинации
    per_page = config['PER_PAGE']  # количество записей на странице
    page = request.args.get('page', 1, type=int)  # получаем номер текущей страницы из запроса, по умолчанию 1

    # Запрос с пагинацией
    detected_spam_list = SpamMessage.query.order_by(SpamMessage.timestamp.desc()).paginate(page=page, per_page=per_page, error_out=False)

    count = detected_spam_list.total
    rows = ""
    for item in detected_spam_list.items:
        date = datetime.fromtimestamp(item.timestamp).strftime("%d.%m.%Y\n%H:%M:%S")
        rows += f"""
                <tr>
                    <td>{date}</td>
                    <td>{item.author_id}</td>
                    <td>{item.author_username or 'N/A'}</td>
                    <td class="spam_message">{item.message_text.replace('\n', '<br>')}</td>
                    <td class="probability">
                        Имеет inline-клавиатуру: {item.has_reply_markup}<br>
                        Забанен CAS / LOLS: {max(item.cas, item.lols)}<br>
                        Вердикт ChatGPT: {0 if not item.chatgpt_prediction else item.chatgpt_prediction}<br>
                        Вердикт RuBert: {item.bert_prediction}
                    </td>
                </tr>
            """

    detected_spam_text_table = f'Обнаруженный спам: {count} {plural_form(count, "запись", "записей", "записи")} (показываются {per_page})'

    # Добавим переменные для навигации по страницам
    prev_url = url_for('main.index', page=detected_spam_list.prev_num) if detected_spam_list.has_prev else None
    next_url = url_for('main.index', page=detected_spam_list.next_num) if detected_spam_list.has_next else None
    total_pages = detected_spam_list.pages  # Общее количество страниц
    current_page = detected_spam_list.page  # Текущая страница

    return render_template(
        'main.html',
        root_css_path=root_css_path,
        main_css_path=main_css_path,
        hamburger_js_path=hamburger_js_path,

        icon_path=icon_path,
        background_path=background_path,

        og_title=title,
        og_description=og_description,
        title=title,
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


@main_bp.route('/spam')
@login_required
def spam():
    return redirect(url_for('main.index'))


@main_bp.route('/about')
@login_required
def about():
    return render_template(
        'about.html',

        root_css_path=root_css_path,
        main_css_path=main_css_path,

        hamburger_js_path=hamburger_js_path,

        icon_path=icon_path,
        background_path=background_path,

        og_title=title,
        og_description=about_text,
        title=title,
        about_text=about_text,
        detected_spam_text=detected_spam_text,
        settings_text=settings_text,
        logout_text=logout_text
    )


@main_bp.route('/settings')
@login_required
def settings():
    return render_template(
        'settings.html',

        root_css_path=root_css_path,
        main_css_path=main_css_path,

        hamburger_js_path=hamburger_js_path,

        icon_path=icon_path,
        background_path=background_path,

        og_title=title,
        og_description=about_text,
        title=title,
        about_text=about_text,
        detected_spam_text=detected_spam_text,
        settings_text=settings_text,
        logout_text=logout_text
    )
