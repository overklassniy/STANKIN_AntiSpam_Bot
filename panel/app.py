import os
import sys
from datetime import timedelta, datetime

from dotenv import load_dotenv
from flask import Flask, session, redirect, url_for
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash

sys.path.append("utils")
from basic import config, logger

# Загрузка переменных окружения
load_dotenv()

db = SQLAlchemy()

# Пути к статическим ресурсам / Переменные
root_css_path = '/static/styles/root.css'

icon_path = '/static/images/stankin-logo.svg'
background_path = '/static/images/stankin_max.svg'

als_font_path = '/static/font/cunia.otf'
als_bold_font_path = '/static/font/FuturaRoundBold.ttf'

title = 'СТАНКИН Анти-Спам'


def create_app():
    app = Flask(__name__)

    if config['TESTING']:
        app.config['DEBUG'] = True

    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'

    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=config['PERMANENT_SESSION_LIFETIME'])
    app.config['REMEMBER_COOKIE_DURATION'] = timedelta(minutes=config['REMEMBER_COOKIE_DURATION'])

    # Обновление времени активности пользователя
    @app.before_request
    def make_session_permanent():
        session.permanent = True
        session.modified = True  # Обновлять время жизни сессии при каждом запросе

    db.init_app(app)

    # Импортируем модели до вызова db.create_all()
    from panel.db_models import SpamMessage, User, MutedUser

    @app.cli.command('init_db')
    def init_db():
        try:
            db.create_all()  # Создание всех таблиц
        except Exception as exception:
            print("Ошибка при вызове db.create_all():", str(exception))
        else:
            print("Таблицы успешно созданы.")

    @app.cli.command('init_admin')
    def init_admin():
        # Добавляем пользователя "admin", если он ещё не существует
        if not User.query.filter_by(name='admin').first():
            db.session.add(User(
                name='admin',
                password=generate_password_hash(os.getenv('ADMIN_PASSWORD'), method='scrypt'),
                can_configure=True
            ))
            db.session.commit()
            print('Пользователь "admin" добавлен.')

    @app.cli.command('init_spam')
    def init_spam():
        """Создаёт тестовое спам-сообщение в базе данных."""
        test_spam = SpamMessage(
            timestamp=datetime.now().timestamp(),
            author_id=123456789,
            author_username="test_user",
            message_text="Это тестовое спам-сообщение.",
            has_reply_markup=False,
            cas=False,
            lols=False,
            chatgpt_prediction=0.8,
            bert_prediction=0.9
        )

        db.session.add(test_spam)
        db.session.commit()
        print("Тестовое спам-сообщение успешно добавлено в базу данных.")

    @app.cli.command('init_muted')
    def init_muted():
        """Создаёт тестового ограниченного пользователя в базе данных."""
        test_muted_user = MutedUser(
            muted_till_timestamp=4102455600
        )

        db.session.add(test_muted_user)
        db.session.commit()
        print("Тестовый ограниченный пользователь успешно добавлен в базу данных.")

    # Настройка Flask-Login
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '<p id="login_message">Пожалуйста, войдите в систему, чтобы получить доступ к панели управления анти&#8209;спам бота.</p>'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))  # Загрузка пользователя по ID

    # Обработка истечения срока авторизации
    @login_manager.needs_refresh_handler
    def refresh_handler():
        return redirect(url_for('auth.login'))

    # Регистрация блюпринтов
    from panel.auth import auth_bp as auth_blueprint
    app.register_blueprint(auth_blueprint)

    from panel.main import main_bp as main_blueprint
    app.register_blueprint(main_blueprint)

    return app
