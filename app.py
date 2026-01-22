import os
import sys
from flask import Flask, render_template, redirect, url_for
from flask_login import LoginManager, current_user
from sqlalchemy import text

app = Flask(__name__, template_folder='templates', static_folder='static')
login_manager = LoginManager()

try:
    app.config.from_pyfile('config.py')
except Exception as e:
    print(f"Ошибка загрузки конфигурации: {e}")
    app.config['SECRET_KEY'] = 'dev-secret-key-temp'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///school_cafeteria.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['DEBUG'] = True

login_manager.init_app(app)
login_manager.login_view = 'auth.login'

from modules.core.database import db

db.init_app(app)

from modules.auth.routes import auth_bp
from modules.user.routes import user_bp
from modules.cook.routes import cook_bp
from modules.admin.routes import admin_bp
from modules.core.models import User

app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(user_bp, url_prefix='/user')
app.register_blueprint(cook_bp, url_prefix='/cook')
app.register_blueprint(admin_bp, url_prefix='/admin')


@login_manager.user_loader
def load_user(user_id):
    with app.app_context():
        return User.query.get(int(user_id))


@app.route('/')
def index():
    if current_user.is_authenticated:
        role_redirects = {
            'student': 'user.dashboard',
            'cook': 'cook.cook_dashboard',
            'admin': 'admin.admin_dashboard'
        }
        redirect_endpoint = role_redirects.get(current_user.role, 'auth.login')
        return redirect(url_for(redirect_endpoint))
    return redirect(url_for('auth.login'))


@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('errors/500.html'), 500


@app.errorhandler(403)
def forbidden(e):
    return render_template('errors/403.html'), 403


if __name__ == '__main__':
    with app.app_context():
        # Создаем необходимые папки
        os.makedirs('instance', exist_ok=True)
        os.makedirs('templates/errors', exist_ok=True)
        os.makedirs('modules/core/services', exist_ok=True)

        # Создаем файл __init__.py в папке services
        services_init_path = 'modules/core/services/__init__.py'
        if not os.path.exists(services_init_path):
            with open(services_init_path, 'w') as f:
                f.write('')

        # Проверяем, существует ли база данных
        db_path = 'instance/school_cafeteria.db'
        db_exists = os.path.exists(db_path)

        if not db_exists:
            print("Создаем таблицы базы данных...")
            db.create_all()

            # Заполняем тестовыми данными
            try:
                from modules.core.seed import seed_database

                seed_database()
            except Exception as e:
                print(f"Не удалось создать тестовые данные: {e}")
        else:
            # Проверяем структуру существующей БД
            try:
                from modules.core.models import User

                # Пытаемся выполнить простой запрос
                test = User.query.first()
                print("База данных подключена успешно")
            except Exception as e:
                print(f"Ошибка структуры БД: {e}")
                print("Пересоздаем таблицы...")
                db.drop_all()
                db.create_all()

                try:
                    from modules.core.seed import seed_database

                    seed_database()
                except Exception as e:
                    print(f"Не удалось создать тестовые данные: {e}")

    app.run(debug=True, host='0.0.0.0', port=8914)
