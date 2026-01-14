from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from modules.core.database import db

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    from modules.core.models import User
    from .forms import LoginForm

    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if user and check_password_hash(user.password, form.password.data):
            # Исправлено: form.remember_me.data вместо form.remember.data
            login_user(user, remember=form.remember_me.data)
            flash(f'Добро пожаловать, {user.full_name}!', 'success')

            if user.role == 'student':
                return redirect(url_for('user.dashboard'))
            elif user.role == 'cook':
                return redirect(url_for('cook.cook_dashboard'))
            elif user.role == 'admin':
                return redirect(url_for('admin.admin_dashboard'))

        flash('Неверный email или пароль', 'danger')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    from modules.core.models import User
    from .forms import RegistrationForm

    form = RegistrationForm()

    if form.validate_on_submit():
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('Пользователь с таким email уже существует', 'warning')
            return redirect(url_for('auth.register'))

        hashed_password = generate_password_hash(
            form.password.data,
            method='pbkdf2:sha256'
        )

        user = User(
            email=form.email.data,
            password=hashed_password,
            role=form.role.data,
            full_name=form.full_name.data,
            class_group=form.class_group.data if form.role.data == 'student' else None
        )

        db.session.add(user)
        db.session.commit()

        flash('Регистрация успешна! Теперь войдите в систему.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы успешно вышли из системы', 'info')
    return redirect(url_for('auth.login'))