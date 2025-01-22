from flask import Flask, render_template

app = Flask(__name__)

# Пути к статическим ресурсам
background_path = '/static/images/stankin_max.svg'

als_font_path = '/static/font/cunia.otf'
als_bold_font_path = '/static/font/FuturaRoundBold.ttf'

main_css_path = '/static/styles/main.css'
login_css_path = '/static/styles/login.css'

# @app.route('/')
# def index(lang='ru'):
#     return render_template(
#         'index.html',
#         # als_font_path=als_font_path,
#         # als_bold_font_path=als_bold_font_path,
#         main_css_path=main_css_path
#     )


@app.route('/login')
def index():
    header_text = 'Добро пожаловать!'
    username_placeholder_text = 'Имя пользователя'
    password_placeholder_text = 'Пароль'
    submit_login_button_text = 'Войти'

    return render_template(
        'login.html',
        # als_font_path=als_font_path,
        # als_bold_font_path=als_bold_font_path,
        main_css_path=main_css_path,
        login_css_path=login_css_path,
        background_path=background_path,

        header_text=header_text,
        username_placeholder_text=username_placeholder_text,
        password_placeholder_text=password_placeholder_text,
        submit_login_button_text=submit_login_button_text,
    )


if __name__ == '__main__':
    from waitress import serve

    # serve(app, host="0.0.0.0", port=8823)
    app.run(host='0.0.0.0', port=8823, debug=True)
