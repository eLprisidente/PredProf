from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from modules.core.models import User


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')


class RegistrationForm(FlaskForm):
    full_name = StringField('ФИО', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    class_group = StringField('Класс', validators=[DataRequired(), Length(min=1, max=10)])
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