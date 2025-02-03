import sys
from typing import Any

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash

from panel.app import background_path, icon_path, title, root_css_path
from panel.db_models import User

sys.path.append("utils")
from basic import config, logger

auth_bp = Blueprint('auth', __name__)

# Пути к статическим ресурсам
login_css_path = '/static/styles/login.css'
login_faq_path = '/static/scripts/login_faq.js'
login_title = title + ': авторизация'


@auth_bp.route('/login')
def login() -> str:
    """
    Формирует страницу входа в систему.

    Возвращает:
        str: Сформированное HTML-содержимое страницы входа.
    """
    logger.info("Отправка страницы входа пользователю.")

    og_description = 'Вход в систему'
    header_text = 'Добро пожаловать!'
    username_placeholder_text = 'Имя пользователя'
    password_placeholder_text = 'Пароль'
    submit_login_button_text = 'Войти'
    remember_me_text = 'Запомните меня!'
    login_faq = 'Как получить доступ к панели управления анти&#8209;спам ботом?'
    login_faq_answer = (
        f'Используйте команду <a id="command" class="command-hidden animate" '
        f'href="https://t.me/{config["BOT_NAME"]}?start=get_password">/get_password</a> в чате с ботом.'
    )

    rendered_page = render_template(
        'login.html',
        root_css_path=root_css_path,
        login_css_path=login_css_path,
        login_faq_path=login_faq_path,
        icon_path=icon_path,
        background_path=background_path,
        og_title=title,
        og_description=og_description,
        title=login_title,
        header_text=header_text,
        username_placeholder_text=username_placeholder_text,
        password_placeholder_text=password_placeholder_text,
        submit_login_button_text=submit_login_button_text,
        remember_me_text=remember_me_text,
        login_faq=login_faq,
        login_faq_answer=login_faq_answer
    )
    logger.info("Страница входа успешно сформирована.")
    return rendered_page


@auth_bp.route('/login', methods=['POST'])
def login_post() -> Any:
    """
    Обрабатывает POST-запрос для входа в систему. Извлекает данные из формы, проверяет корректность
    введенных данных и осуществляет вход пользователя.
    """
    username: str = request.form.get('username', '')
    password: str = request.form.get('password', '')
    remember: bool = True if request.form.get('remember') else False

    logger.info("Получен POST-запрос для входа. Имя пользователя: '%s'.", username)

    user = User.query.filter_by(name=username).first()

    if not user:
        logger.warning("Пользователь с именем '%s' не найден.", username)
    elif not check_password_hash(user.password, password):
        logger.warning("Неверный пароль для пользователя '%s'.", username)

    if not user or not check_password_hash(user.password, password):
        flash('<p id="login_message">Пожалуйста, проверьте свои данные для входа в систему и повторите попытку.</p>')
        logger.info("Неудачная попытка входа для пользователя '%s'.", username)
        return redirect(url_for('auth.login'))

    if current_user.is_authenticated:
        logger.info("Существующий пользователь '%s' уже аутентифицирован, выполняется выход.", current_user.id)
        logout_user()

    login_user(user, remember=remember)
    logger.info("Пользователь '%s' успешно вошел в систему.", username)
    return redirect(url_for('main.index'))


@auth_bp.route('/logout')
@login_required
def logout() -> Any:
    """
    Выходит из системы и перенаправляет пользователя на главную страницу.
    """
    logger.info("Пользователь '%s' выполняет выход из системы.", current_user.id)
    logout_user()
    logger.info("Пользователь успешно вышел из системы.")
    return redirect(url_for('main.index'))
