from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from modules.core.models import User


class LoginForm(FlaskForm):
    """Форма входа в систему"""
    email = StringField('Email', validators=[
        DataRequired(message='Email обязателен'),
        Email(message='Некорректный email адрес')
    ], render_kw={"placeholder": "example@school.ru"})

    password = PasswordField('Пароль', validators=[
        DataRequired(message='Пароль обязателен'),
        Length(min=6, message='Пароль должен содержать минимум 6 символов')
    ], render_kw={"placeholder": "Введите пароль"})

    remember = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')


class RegistrationForm(FlaskForm):
    """Форма регистрации"""
    email = StringField('Email', validators=[
        DataRequired(message='Email обязателен'),
        Email(message='Некорректный email адрес')
    ], render_kw={"placeholder": "example@school.ru"})

    password = PasswordField('Пароль', validators=[
        DataRequired(message='Пароль обязателен'),
        Length(min=6, message='Пароль должен содержать минимум 6 символов'),
        EqualTo('confirm_password', message='Пароли должны совпадать')
    ], render_kw={"placeholder": "Придумайте пароль"})

    confirm_password = PasswordField('Подтвердите пароль', validators=[
        DataRequired(message='Подтверждение пароля обязательно')
    ], render_kw={"placeholder": "Повторите пароль"})

    role = SelectField('Роль', choices=[
        ('student', 'Ученик'),
        ('cook', 'Повар'),
        ('admin', 'Администратор')
    ], validators=[DataRequired(message='Выберите роль')])

    full_name = StringField('ФИО', validators=[
        DataRequired(message='ФИО обязательно'),
        Length(min=2, max=100, message='ФИО должно быть от 2 до 100 символов')
    ], render_kw={"placeholder": "Иванов Иван Иванович"})

    class_group = StringField('Класс (только для учеников)',
                              render_kw={"placeholder": "10А"})

    submit = SubmitField('Зарегистрироваться')

    def validate_email(self, email):
        """Проверка уникальности email"""
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Пользователь с таким email уже существует')