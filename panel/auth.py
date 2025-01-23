from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user
from werkzeug.security import check_password_hash

from panel.app import background_path
from panel.main import main_css_path
from panel.db_models import User

auth_bp = Blueprint('auth', __name__)

# Пути к статическим ресурсам
login_css_path = '/static/styles/login.css'


@auth_bp.route('/login')
def login():
    header_text = 'Добро пожаловать!'
    username_placeholder_text = 'Имя пользователя'
    password_placeholder_text = 'Пароль'
    submit_login_button_text = 'Войти'
    remember_me_text = 'Запомните меня!'

    return render_template(
        'login.html',
        main_css_path=main_css_path,
        login_css_path=login_css_path,
        background_path=background_path,

        header_text=header_text,
        username_placeholder_text=username_placeholder_text,
        password_placeholder_text=password_placeholder_text,
        submit_login_button_text=submit_login_button_text,
        remember_me_text=remember_me_text
    )


@auth_bp.route('/login', methods=['POST'])
def login_post():
    username = request.form.get('username')
    password = request.form.get('password')
    remember = True if request.form.get('remember') else False

    user = User.query.filter_by(name=username).first()

    if not user or not check_password_hash(user.password, password):
        flash('Пожалуйста, проверьте свои данные для входа в систему и повторите попытку.')
        return redirect(url_for('auth.login'))

    login_user(user, remember=remember)

    return redirect(url_for('main.index'))


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))
