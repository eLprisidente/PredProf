from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, Optional
from modules.core.models import User


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')


class RegistrationForm(FlaskForm):
    full_name = StringField('ФИО', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])

    # Поле класса теперь необязательное
    class_group = StringField('Класс', validators=[Optional(), Length(max=10)])

    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Подтвердите пароль',
                                     validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Роль', choices=[
        ('student', 'Ученик'),
        ('cook', 'Повар'),
        ('admin', 'Администратор')
    ], default='student')
    submit = SubmitField('Зарегистрироваться')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Этот email уже зарегистрирован')

    def validate_class_group(self, class_group):
        """Валидация класса в зависимости от роли"""
        if self.role.data == 'student':
            if not class_group.data or not class_group.data.strip():
                raise ValidationError('Для ученика необходимо указать класс')
            if len(class_group.data.strip()) > 10:
                raise ValidationError('Класс не должен превышать 10 символов')