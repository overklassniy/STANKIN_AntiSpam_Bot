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
sys.path.append("..")
from utils.basic import config, logger

# Загрузка переменных окружения
load_dotenv()

# Инициализация базы данных
db = SQLAlchemy()

# Пути к статическим ресурсам и другие переменные
root_css_path = '/static/styles/root.css'
icon_path = '/static/images/stankin-logo.svg'
background_path = '/static/images/stankin_max.svg'
als_font_path = '/static/font/cunia.otf'
als_bold_font_path = '/static/font/FuturaRoundBold.ttf'
title = 'СТАНКИН Анти-Спам'

main_css_path = '/static/styles/main.css'
hamburger_js_path = '/static/scripts/hamburger.js'

exception_css_path = '/static/styles/exception.css'


def create_app() -> Flask:
    """
    Создаёт и настраивает экземпляр приложения Flask.
    """
    app = Flask(__name__)

    # Включение режима отладки, если тестирование активно
    if config['TESTING']:
        app.config['DEBUG'] = True
        logger.info("Режим тестирования включён, DEBUG=True.")

    # Конфигурация секретного ключа и базы данных
    secret_key: Optional[str] = os.getenv('SECRET_KEY')
    if not secret_key:
        logger.error("SECRET_KEY не найден в переменных окружения!")
        raise Exception("SECRET_KEY не задан!")
    app.config['SECRET_KEY'] = secret_key

    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
    logger.debug("SQLAlchemy настроен на использование SQLite базы данных.")

    # Настройка времени жизни сессии
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=config['PERMANENT_SESSION_LIFETIME'])
    app.config['REMEMBER_COOKIE_DURATION'] = timedelta(minutes=config['REMEMBER_COOKIE_DURATION'])
    logger.debug("Настроены параметры времени жизни сессии.")

    # Обновление времени активности пользователя перед каждым запросом
    @app.before_request
    def make_session_permanent() -> None:
        """
        Делает сессию постоянной и обновляет время её жизни при каждом запросе.
        """
        session.permanent = True
        session.modified = True
        logger.debug(f"Сессия обновлена для запроса {request.path}")

    # Инициализация базы данных в приложении
    db.init_app(app)
    logger.info("База данных инициализирована в приложении.")

    # Импорт моделей после инициализации БД
    from panel.db_models import SpamMessage, User, MutedUser

    # Команда для инициализации базы данных
    @app.cli.command('init_db')
    def init_db() -> None:
        """
        Инициализирует базу данных, создавая все таблицы.
        """
        try:
            db.create_all()
        except Exception as exception:
            print("Ошибка при вызове db.create_all():", str(exception))
        else:
            print("Таблицы успешно созданы.")

    # Команда для инициализации администратора
    @app.cli.command('init_admin')
    def init_admin() -> None:
        """
        Инициализирует администратора, добавляя пользователя 'admin' в базу данных, если он не существует.
        """
        if not User.query.filter_by(name='admin').first():
            try:
                admin_password: str = os.getenv('ADMIN_PASSWORD')
                if not admin_password:
                    print('ADMIN_PASSWORD не задан в переменных окружения!')
                    return
                db.session.add(User(
                    name='admin',
                    password=generate_password_hash(admin_password, method='scrypt'),
                    can_configure=True
                ))
                db.session.commit()
                print('Пользователь "admin" добавлен.')
            except Exception as e:
                print("Ошибка при добавлении пользователя admin:", e)
        else:
            print('Пользователь "admin" уже существует.')

    # Команда для создания тестового спам-сообщения
    @app.cli.command('init_spam')
    def init_spam() -> None:
        """
        Создаёт тестовое спам-сообщение в базе данных.
        """
        try:
            test_spam = SpamMessage(
                timestamp=datetime.now().timestamp(),
                author_id=123456789,
                author_username="test_user",
                message_text="Это тестовое спам-сообщение.",
                has_reply_markup=False,
                cas=False,
                lols=False,
                chatgpt_prediction=1,
                bert_prediction=0.99
            )
            db.session.add(test_spam)
            db.session.commit()
            print("Тестовое спам-сообщение успешно добавлено в базу данных.")
        except Exception as e:
            print("Ошибка при добавлении тестового спам-сообщения:", e)

    # Команда для создания тестового ограниченного пользователя
    @app.cli.command('init_muted')
    def init_muted() -> None:
        """
        Создаёт тестового ограниченного пользователя в базе данных.
        """
        try:
            test_muted_user = MutedUser(
                id=1234567890,
                username='test_user',
                timestamp=datetime.now().timestamp(),
                muted_till_timestamp=4102455600  # Примерное время в будущем
            )
            db.session.add(test_muted_user)
            db.session.commit()
            print("Тестовый ограниченный пользователь успешно добавлен в базу данных.")
        except Exception as e:
            print("Ошибка при добавлении тестового ограниченного пользователя:", e)

    # Настройка Flask-Login
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message = (
        '<p id="login_message">Пожалуйста, войдите в систему, чтобы получить доступ к панели управления анти‑спам бота.</p>'
    )
    login_manager.init_app(app)
    logger.info("Flask-Login успешно настроен.")

    @login_manager.user_loader
    def load_user(user_id: str) -> Optional[User]:
        """
        Загружает пользователя по его идентификатору.

        Аргументы:
            user_id (str): Идентификатор пользователя.

        Возвращает:
            User | None: Объект пользователя, если найден, иначе None.
        """
        logger.debug("Загрузка пользователя по ID: %s", user_id)
        return User.query.get(int(user_id))

    @login_manager.needs_refresh_handler
    def refresh_handler() -> Any:
        """
        Обрабатывает ситуацию, когда требуется обновление сессии пользователя.
        """
        return redirect(url_for('auth.login'))

    @app.errorhandler(404)
    def page_not_found():
        """
        Вывод кастомной страницы ошибки.
        """

        og_description = 'Упс!'
        oops_text = 'Упс! Что-то пошло не так...<br>Возможно, вы заблудились?'
        back_button_text = 'На главную'

        return render_template(
            'exception.html',
            root_css_path=root_css_path,
            main_css_path=main_css_path,
            exception_css_path=exception_css_path,

            icon_path=icon_path,
            background_path=background_path,

            og_title=title,
            og_description=og_description,
            title=title,
            oops_text=oops_text,
            back_button_text=back_button_text
        ), 404

    # Регистрация блюпринтов
    try:
        from panel.auth import auth_bp as auth_blueprint
        app.register_blueprint(auth_blueprint)
        logger.info("Блюпринт авторизации успешно зарегистрирован.")
    except Exception as e:
        logger.error("Ошибка при регистрации блюпринта авторизации: %s", e)

    try:
        from panel.main import main_bp as main_blueprint
        app.register_blueprint(main_blueprint)
        logger.info("Блюпринт основного модуля успешно зарегистрирован.")
    except Exception as e:
        logger.error("Ошибка при регистрации основного блюпринта: %s", e)

    logger.info("Приложение Flask успешно создано и настроено.")
    return app
