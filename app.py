import os
import sys
from flask import Flask, render_template, redirect, url_for, session
from flask_login import LoginManager, current_user
from sqlalchemy import text
import traceback
from datetime import datetime, date

from flask_wtf.csrf import generate_csrf

app = Flask(__name__,
            template_folder='templates',
            static_folder='static',
            instance_relative_config=True)
login_manager = LoginManager()

try:
    app.config.from_pyfile('config.py')
except Exception as e:
    print(f"{e}")
    app.config['SECRET_KEY'] = 'dev-secret-key-temp-please-change-in-production'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///school_cafeteria.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['DEBUG'] = True
    app.config['UPLOAD_FOLDER'] = 'static/uploads'
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
    app.config['WTF_CSRF_ENABLED'] = True  # Включаем CSRF

login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Пожалуйста, войдите в систему для доступа к этой странице.'
login_manager.login_message_category = 'info'

from modules.core.database import db

db.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    try:
        from modules.core.models import User
        return User.query.get(int(user_id))
    except Exception as e:
        print(f"{user_id}: {e}")
        return None


with app.app_context():
    try:
        folders = [
            'instance',
            'static/uploads/avatars',
            'static/uploads/menu_items',
            'templates/errors',
            'modules/core/services'
        ]

        for folder in folders:
            os.makedirs(folder, exist_ok=True)
            print(f"{folder}")

        services_init_path = 'modules/core/services/__init__.py'
        if not os.path.exists(services_init_path):
            with open(services_init_path, 'w', encoding='utf-8') as f:
                f.write('# Сервисный модуль\n')

    except Exception as e:
        print(f"{e}")
        traceback.print_exc()

try:
    from modules.auth.routes import auth_bp
    from modules.user.routes import user_bp
    from modules.cook.routes import cook_bp
    from modules.admin.routes import admin_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(user_bp, url_prefix='/user')
    app.register_blueprint(cook_bp, url_prefix='/cook')
    app.register_blueprint(admin_bp, url_prefix='/admin')

except ImportError as e:
    print(f"{e}")
    traceback.print_exc()
    sys.exit(1)

from modules.user.routes import get_cart_count


@app.context_processor
def inject_cart_count():
    return {'cart_count': get_cart_count()}


@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}


@app.context_processor
def inject_today():
    return {'today': date.today()}


@app.context_processor
def inject_csrf_token():
    try:
        def get_csrf_token():
            return generate_csrf()
        return {'csrf_token': get_csrf_token}
    except Exception as e:
        print(f"Ошибка в inject_csrf_token: {e}")
        return {'csrf_token': lambda: ''}


@app.context_processor
def inject_subscription_info():
    if current_user.is_authenticated:
        try:
            from modules.user.services import SubscriptionService
            active_subscription = SubscriptionService.get_active_subscription(current_user.id)
            return {
                'active_subscription': active_subscription,
                'has_active_subscription': active_subscription is not None,
                'day_price': SubscriptionService.DAY_PRICE
            }
        except Exception as e:
            print(f"Ошибка получения информации об абонементе: {e}")
            return {
                'active_subscription': None,
                'has_active_subscription': False,
                'day_price': 150.0
            }
    return {
        'active_subscription': None,
        'has_active_subscription': False,
        'day_price': 150.0
    }


@app.context_processor
def inject_order_counts():
    from datetime import date

    if current_user.is_authenticated and current_user.role == 'cook':
        try:
            from modules.core.models import Order

            today_orders = Order.query.filter(
                Order.order_date == date.today(),
                Order.status.in_(['pending', 'preparing', 'ready'])
            ).all()

            total_active = len(today_orders)

            return {
                'cook_total_active': total_active
            }
        except Exception as e:
            print(f"Ошибка получения счетчиков для повара: {e}")
            return {
                'cook_total_active': 0
            }

    elif current_user.is_authenticated and current_user.role == 'admin':
        try:
            from modules.core.models import SupplyRequest

            pending_requests_count = SupplyRequest.query.filter_by(status='pending').count()

            return {
                'pending_requests_count': pending_requests_count
            }
        except Exception as e:
            print(f"Ошибка получения счетчиков для админа: {e}")
            return {
                'pending_requests_count': 0
            }

    elif current_user.is_authenticated and current_user.role == 'cook':
        try:
            from modules.core.models import SupplyRequest

            pending_requests_count = SupplyRequest.query.filter_by(status='pending').count()

            return {
                'pending_requests_count': pending_requests_count
            }
        except Exception as e:
            print(f"Ошибка получения счетчиков заявок для повара: {e}")
            return {
                'pending_requests_count': 0
            }

    return {
        'cook_total_active': 0,
        'pending_requests_count': 0
    }


@app.context_processor
def inject_pending_counts():
    if current_user.is_authenticated:
        if current_user.role == 'cook':
            from modules.core.models import SupplyRequest, Order
            from datetime import date

            pending_requests_count = SupplyRequest.query.filter_by(
                status='pending'
            ).count()

            pending_orders_count = Order.query.filter(
                Order.order_date == date.today(),
                Order.status != 'received'
            ).count()

            return {
                'pending_requests_count': pending_requests_count,
                'pending_orders_count': pending_orders_count
            }
        elif current_user.role == 'admin':
            from modules.core.models import SupplyRequest
            pending_requests_count = SupplyRequest.query.filter_by(
                status='pending'
            ).count()
            return {'pending_requests_count': pending_requests_count}

    return {}


@app.context_processor
def inject_pending_requests():
    from modules.core.models import SupplyRequest
    try:
        if current_user.is_authenticated and current_user.role == 'admin':
            pending_count = SupplyRequest.query.filter_by(status='pending').count()
            return {'pending_requests_count': pending_count}
    except:
        pass
    return {'pending_requests_count': 0}


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


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/health')
def health_check():
    try:
        with db.engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        return {'status': 'healthy', 'database': 'connected'}, 200
    except Exception as e:
        return {'status': 'unhealthy', 'error': str(e)}, 500


@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('errors/500.html'), 500


@app.errorhandler(403)
def forbidden(e):
    return render_template('errors/403.html'), 403


@app.errorhandler(401)
def unauthorized(e):
    return redirect(url_for('auth.login'))


def migrate_database():
    """Миграция для добавления новых таблиц и полей"""
    with app.app_context():
        from sqlalchemy import text

        try:
            with db.engine.connect() as conn:
                # 1. Добавляем поле is_deleted в menu_items
                result = conn.execute(text("PRAGMA table_info(menu_items)"))
                columns = [col[1] for col in result.fetchall()]

                if 'is_deleted' not in columns:
                    print("Добавляем поле is_deleted в таблицу menu_items...")
                    conn.execute(text("ALTER TABLE menu_items ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE"))

                # 2. Добавляем поля для возврата средств в orders
                result = conn.execute(text("PRAGMA table_info(orders)"))
                columns = [col[1] for col in result.fetchall()]

                if 'refunded' not in columns:
                    print("Добавляем поле refunded в таблицу orders...")
                    conn.execute(text("ALTER TABLE orders ADD COLUMN refunded BOOLEAN DEFAULT FALSE"))

                if 'refund_amount' not in columns:
                    print("Добавляем поле refund_amount в таблицу orders...")
                    conn.execute(text("ALTER TABLE orders ADD COLUMN refund_amount FLOAT DEFAULT 0.0"))

                if 'refund_date' not in columns:
                    print("Добавляем поле refund_date в таблицу orders...")
                    conn.execute(text("ALTER TABLE orders ADD COLUMN refund_date DATETIME"))

                # 3. Проверяем существование таблицы transactions
                tables = conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table' AND name='transactions'")).fetchall()

                if not tables:
                    print("Создаем таблицу transactions...")
                    conn.execute(text('''
                        CREATE TABLE transactions (
                            id INTEGER PRIMARY KEY,
                            user_id INTEGER NOT NULL,
                            order_id INTEGER,
                            amount FLOAT NOT NULL,
                            transaction_type VARCHAR(20) NOT NULL,
                            status VARCHAR(20) DEFAULT 'pending',
                            description TEXT,
                            created_at DATETIME,
                            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                            FOREIGN KEY (order_id) REFERENCES orders (id) ON DELETE SET NULL
                        )
                    '''))

                # 4. Проверяем существование таблицы supply_requests
                tables = conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table' AND name='supply_requests'")).fetchall()


                if tables:
                    # Таблица существует, проверяем колонки
                    result = conn.execute(text("PRAGMA table_info(supply_requests)"))
                    columns = [col[1] for col in result.fetchall()]

                    if 'approved_at' not in columns:
                        print("Добавляем поле approved_at в таблицу supply_requests...")
                        conn.execute(text("ALTER TABLE supply_requests ADD COLUMN approved_at DATETIME"))

                    if 'approved_by' not in columns:
                        print("Добавляем поле approved_by в таблицу supply_requests...")
                        conn.execute(text("ALTER TABLE supply_requests ADD COLUMN approved_by INTEGER"))

                print("Миграция базы данных завершена!")

        except Exception as e:
            print(f"Ошибка миграции: {e}")
            traceback.print_exc()


def init_database():
    """Инициализация базы данных"""
    with app.app_context():
        # Проверяем, существует ли база данных
        db_path = 'instance/school_cafeteria.db'
        db_exists = os.path.exists(db_path)

        if not db_exists:
            try:
                db.create_all()

                # Заполняем тестовыми данными
                try:
                    from modules.core.seed import seed_database
                    seed_database()
                except ImportError as e:
                    print(f"{e}")
                    traceback.print_exc()
                except Exception as e:
                    print(f"{e}")
                    traceback.print_exc()

            except Exception as e:
                print(f"{e}")
                traceback.print_exc()
        else:
            # Проверяем структуру существующей БД
            try:
                from modules.core.models import User
                test = User.query.first()

                # Запускаем дополнительную миграцию для внешних ключей
                print("Запускаем миграцию внешних ключей...")
                migrate_database()

            except Exception as e:
                print(f"{e}")
                try:
                    db.drop_all()
                    db.create_all()

                    # Заполняем тестовыми данными
                    try:
                        from modules.core.seed import seed_database
                        seed_database()
                    except Exception as e:
                        print(f"{e}")

                except Exception as e:
                    print(f"{e}")
                    traceback.print_exc()

        # Запускаем скрипт обновления внешних ключей
        try:
            print("Запускаем обновление внешних ключей...")
            from migrations.update_foreign_keys import update_foreign_keys
            if update_foreign_keys():
                print("Внешние ключи успешно обновлены!")
        except Exception as e:
            print(f"Ошибка при обновлении внешних ключей: {e}")


if __name__ == '__main__':
    init_database()
    app.run(debug=True, host='0.0.0.0', port=8146)
