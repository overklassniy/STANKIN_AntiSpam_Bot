import os
import sys
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask, session
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash

sys.path.append("utils")
from basic import config, logger

# Загрузка переменных окружения
load_dotenv()

db = SQLAlchemy()

# Пути к статическим ресурсам
background_path = '/static/images/stankin_max.svg'
als_font_path = '/static/font/cunia.otf'
als_bold_font_path = '/static/font/FuturaRoundBold.ttf'


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
    from panel.db_models import User

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
            db.session.add(User(name='admin', password=generate_password_hash(os.getenv('ADMIN_PASSWORD'), method='scrypt')))
            db.session.commit()
            print("Пользователь 'admin' добавлен.")

    # Настройка Flask-Login
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Пожалуйста, войдите в систему, чтобы получить доступ к этой странице.'
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
