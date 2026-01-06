"""
Модуль авторизации для панели управления.
"""

from typing import Any

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash

from panel.app import background_path, icon_path, title, root_css_path
from panel.db_models import User
from utils.config import BOT_NAME
from utils.logging import logger

auth_bp = Blueprint('auth', __name__)

# Пути к статическим ресурсам
LOGIN_CSS_PATH = '/static/styles/login.css'
LOGIN_FAQ_JS_PATH = '/static/scripts/login_faq.js'


@auth_bp.route('/login')
def login() -> str:
    """
    Формирует страницу входа в систему.
    """
    logger.info("Отправка страницы входа.")

    return render_template(
        'login.html',
        root_css_path=root_css_path,
        login_css_path=LOGIN_CSS_PATH,
        login_faq_path=LOGIN_FAQ_JS_PATH,
        icon_path=icon_path,
        background_path=background_path,
        og_title=title,
        og_description='Вход в систему',
        title=f'{title}: авторизация',
        header_text='Добро пожаловать!',
        username_placeholder_text='Имя пользователя',
        password_placeholder_text='Пароль',
        submit_login_button_text='Войти',
        remember_me_text='Запомните меня!',
        login_faq='Как получить доступ к панели управления?',
        login_faq_answer=(
            f'Используйте команду <a id="command" class="command-hidden animate" '
            f'href="https://t.me/{BOT_NAME}?start=get_password">/get_password</a> в чате с ботом.'
        )
    )


@auth_bp.route('/login', methods=['POST'])
def login_post() -> Any:
    """
    Обрабатывает POST-запрос для входа в систему.
    """
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    remember = bool(request.form.get('remember'))

    logger.info(f"Попытка входа: '{username}'")

    # Поиск пользователя
    user = User.query.filter_by(name=username).first()

    # Проверка учетных данных
    if not user or not check_password_hash(user.password, password):
        flash(
            '<p id="login_message">Пожалуйста, проверьте данные для входа и повторите попытку.</p>'
        )
        logger.warning(f"Неудачная попытка входа: '{username}'")
        return redirect(url_for('auth.login'))

    # Выход из текущей сессии
    if current_user.is_authenticated:
        logger.info(f"Пользователь {current_user.id} уже аутентифицирован, выполняется переход.")
        logout_user()

    # Вход
    login_user(user, remember=remember)
    logger.info(f"Пользователь '{username}' успешно вошёл в систему.")
    return redirect(url_for('main.index'))


@auth_bp.route('/logout')
@login_required
def logout() -> Any:
    """
    Выход из системы.
    """
    user_id = current_user.id
    logout_user()
    logger.info(f"Пользователь {user_id} вышел из системы.")
    return redirect(url_for('main.index'))
