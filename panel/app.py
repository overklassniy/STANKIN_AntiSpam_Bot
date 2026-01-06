"""
Модуль приложения Flask для панели управления.
"""

import os
import sys
from datetime import timedelta, datetime
from typing import Any, Optional

from dotenv import load_dotenv
from flask import Flask, session, redirect, url_for, request, render_template
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash

# Добавляем путь для импорта утилит
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config import (
    DATABASE_DIR, DATABASE_PATH, SECRET_KEY, ADMIN_PASSWORD,
    PERMANENT_SESSION_LIFETIME, REMEMBER_COOKIE_DURATION,
    TESTING, DEFAULT_SETTINGS
)
from utils.logging import logger

# Загрузка переменных окружения
load_dotenv()

# Инициализация базы данных
db = SQLAlchemy()

# Пути к статическим ресурсам
STATIC_PATHS = {
    'root_css': '/static/styles/root.css',
    'main_css': '/static/styles/main.css',
    'exception_css': '/static/styles/exception.css',
    'hamburger_js': '/static/scripts/hamburger.js',
    'icon': '/static/images/stankin-logo.svg',
    'background': '/static/images/stankin_max.svg',
    'cunia_font': '/static/font/cunia.otf',
    'futura_font': '/static/font/FuturaRoundBold.ttf',
}

# Для обратной совместимости
root_css_path = STATIC_PATHS['root_css']
icon_path = STATIC_PATHS['icon']
background_path = STATIC_PATHS['background']
als_font_path = STATIC_PATHS['cunia_font']
als_bold_font_path = STATIC_PATHS['futura_font']
main_css_path = STATIC_PATHS['main_css']
hamburger_js_path = STATIC_PATHS['hamburger_js']
exception_css_path = STATIC_PATHS['exception_css']

TITLE = 'СТАНКИН Анти-Спам'
title = TITLE  # Для обратной совместимости


def create_app() -> Flask:
    """
    Создаёт и настраивает экземпляр приложения Flask.
    """
    app = Flask(__name__)

    # Режим отладки
    if TESTING:
        app.config['DEBUG'] = True
        logger.info("Режим тестирования включён.")

    # Конфигурация секретного ключа
    if not SECRET_KEY:
        logger.error("SECRET_KEY не найден в переменных окружения!")
        raise ValueError("SECRET_KEY не задан!")
    app.config['SECRET_KEY'] = SECRET_KEY

    # Конфигурация базы данных
    os.makedirs(DATABASE_DIR, exist_ok=True)
    # На Windows нужен формат sqlite:///C:/path, на Unix sqlite:////path
    db_path = DATABASE_PATH.replace('\\', '/')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    logger.debug(f"База данных: {db_path}")

    # Настройка сессий
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=PERMANENT_SESSION_LIFETIME)
    app.config['REMEMBER_COOKIE_DURATION'] = timedelta(minutes=REMEMBER_COOKIE_DURATION)

    @app.before_request
    def make_session_permanent() -> None:
        """Делает сессию постоянной."""
        session.permanent = True
        session.modified = True

    # Инициализация базы данных
    db.init_app(app)
    logger.info("База данных инициализирована.")

    # Импорт моделей
    from panel.db_models import SpamMessage, User, MutedUser, Setting, CollectedMessage

    # CLI команды
    _register_cli_commands(app, db, User, SpamMessage, MutedUser, Setting)

    # Настройка Flask-Login
    _setup_login_manager(app, User)

    # Обработчики ошибок
    _register_error_handlers(app)

    # Регистрация блюпринтов
    _register_blueprints(app)

    logger.info("Приложение Flask успешно создано.")
    return app


def _register_cli_commands(app, db, User, SpamMessage, MutedUser, Setting):
    """Регистрирует CLI команды Flask."""

    @app.cli.command('init_db')
    def init_db() -> None:
        """Инициализирует базу данных."""
        try:
            db.create_all()

            # Инициализируем настройки по умолчанию
            descriptions = {
                'BERT_THRESHOLD': 'Порог классификации BERT (0-1)',
                'BERT_SURE_THRESHOLD': 'Порог уверенности для авто-действий (0-1)',
                'CHECK_REPLY_MARKUP': 'Проверять наличие inline-клавиатуры',
                'CHECK_CAS': 'Проверять пользователей через CAS API',
                'CHECK_LOLS': 'Проверять пользователей через LOLS API',
                'ENABLE_CHATGPT': 'Использовать ChatGPT для анализа',
                'ENABLE_DELETING': 'Автоматически удалять спам',
                'ENABLE_AUTOMUTING': 'Автоматически ограничивать спамеров',
                'COLLECT_ALL_MESSAGES': 'Собирать все сообщения для анализа',
                'PER_PAGE': 'Записей на странице в панели',
            }

            for key, value in DEFAULT_SETTINGS.items():
                if not Setting.query.get(key):
                    Setting.set_value(key, value, description=descriptions.get(key, ''))

            db.session.commit()
            logger.info("Таблицы базы данных созданы.")
            print("Таблицы успешно созданы.")
        except Exception as e:
            logger.error(f"Ошибка создания таблиц: {e}")
            print(f"Ошибка: {e}")

    @app.cli.command('init_admin')
    def init_admin() -> None:
        """Создаёт администратора."""
        if User.query.filter_by(name='admin').first():
            logger.info('Пользователь "admin" уже существует.')
            print('Пользователь "admin" уже существует.')
            return

        if not ADMIN_PASSWORD:
            logger.error('ADMIN_PASSWORD не задан!')
            print('ADMIN_PASSWORD не задан!')
            return

        try:
            db.session.add(User(
                name='admin',
                password=generate_password_hash(ADMIN_PASSWORD, method='scrypt'),
                can_configure=True
            ))
            db.session.commit()
            logger.info('Пользователь "admin" добавлен.')
            print('Пользователь "admin" добавлен.')
        except Exception as e:
            logger.error(f"Ошибка добавления admin: {e}")
            print(f"Ошибка: {e}")

    @app.cli.command('init_spam')
    def init_spam() -> None:
        """Создаёт тестовое спам-сообщение."""
        try:
            db.session.add(SpamMessage(
                timestamp=datetime.now().timestamp(),
                author_id=123456789,
                author_username="test_user",
                message_text="Это тестовое спам-сообщение.",
                has_reply_markup=False,
                cas=False,
                lols=False,
                chatgpt_prediction=1,
                bert_prediction=0.99
            ))
            db.session.commit()
            logger.info("Тестовое спам-сообщение добавлено.")
            print("Тестовое спам-сообщение добавлено.")
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            print(f"Ошибка: {e}")

    @app.cli.command('init_muted')
    def init_muted() -> None:
        """Создаёт тестового ограниченного пользователя."""
        try:
            db.session.add(MutedUser(
                id=1234567890,
                username='test_user',
                timestamp=datetime.now().timestamp(),
                muted_till_timestamp=4102455600
            ))
            db.session.commit()
            logger.info("Тестовый ограниченный пользователь добавлен.")
            print("Тестовый ограниченный пользователь добавлен.")
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            print(f"Ошибка: {e}")


def _setup_login_manager(app, User):
    """Настраивает Flask-Login."""
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message = (
        '<p id="login_message">Пожалуйста, войдите в систему для доступа к панели управления.</p>'
    )
    login_manager.init_app(app)
    logger.info("Flask-Login настроен.")

    @login_manager.user_loader
    def load_user(user_id: str) -> Optional[User]:
        """Загружает пользователя по ID."""
        try:
            return User.query.get(int(user_id))
        except Exception as e:
            logger.error(f"Ошибка загрузки пользователя {user_id}: {e}")
            return None

    @login_manager.needs_refresh_handler
    def refresh_handler() -> Any:
        """Обрабатывает необходимость обновления сессии."""
        return redirect(url_for('auth.login'))


def _register_error_handlers(app):
    """Регистрирует обработчики ошибок."""

    @app.errorhandler(404)
    def page_not_found(error):
        """Страница не найдена."""
        logger.warning(f"404: {request.path}")
        return render_template(
            'exception.html',
            root_css_path=root_css_path,
            main_css_path=main_css_path,
            exception_css_path=exception_css_path,
            icon_path=icon_path,
            background_path=background_path,
            og_title=TITLE,
            og_description='Упс!',
            title=TITLE,
            oops_text='Упс! Что-то пошло не так...<br>Возможно, вы заблудились?',
            back_button_text='На главную'
        ), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Внутренняя ошибка сервера."""
        logger.error(f"500: {error}")
        return render_template(
            'exception.html',
            root_css_path=root_css_path,
            main_css_path=main_css_path,
            exception_css_path=exception_css_path,
            icon_path=icon_path,
            background_path=background_path,
            og_title=TITLE,
            og_description='Ошибка сервера',
            title=TITLE,
            oops_text='Упс! Произошла внутренняя ошибка сервера.<br>Попробуйте позже.',
            back_button_text='На главную'
        ), 500


def _register_blueprints(app):
    """Регистрирует блюпринты."""
    try:
        from panel.auth import auth_bp
        app.register_blueprint(auth_bp)
        logger.info("Блюпринт auth зарегистрирован.")
    except Exception as e:
        logger.error(f"Ошибка регистрации auth: {e}")

    try:
        from panel.main import main_bp
        app.register_blueprint(main_bp)
        logger.info("Блюпринт main зарегистрирован.")
    except Exception as e:
        logger.error(f"Ошибка регистрации main: {e}")
