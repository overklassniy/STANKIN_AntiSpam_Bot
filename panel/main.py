from flask import Blueprint, render_template
from flask_login import login_required, current_user

main_bp = Blueprint('main', __name__)

# Пути к статическим ресурсам
main_css_path = '/static/styles/main.css'


@main_bp.route('/')
@login_required
def index():
    return render_template('main.html', name=current_user.name)
