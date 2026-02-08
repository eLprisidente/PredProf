from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user
from sqlalchemy.exc import SQLAlchemyError


def handle_db_errors(func):

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SQLAlchemyError as e:
            print(f"Database error: {e}")
            flash('Произошла ошибка базы данных. Попробуйте позже.', 'danger')
            return redirect(url_for('index'))

    return wrapper


def role_required(role):

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Требуется авторизация', 'warning')
                return redirect(url_for('auth.login'))

            if current_user.role != role:
                flash('Доступ запрещен для вашей роли', 'danger')
                return redirect(url_for('index'))

            return func(*args, **kwargs)

        return wrapper

    return decorator