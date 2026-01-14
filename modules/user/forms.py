from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, SelectField, IntegerField, TextAreaField, SubmitField, DateField, RadioField
from wtforms.validators import DataRequired, NumberRange, Optional, Length, Email
from datetime import datetime


class OrderForm(FlaskForm):
    """Форма заказа питания"""
    menu_item_id = SelectField('Блюдо', coerce=int, validators=[DataRequired()])
    meal_time = SelectField('Время приема пищи', choices=[
        ('breakfast', 'Завтрак'),
        ('lunch', 'Обед')
    ], validators=[DataRequired()])

    quantity = IntegerField('Количество', validators=[
        DataRequired(),
        NumberRange(min=1, max=5, message='Можно заказать от 1 до 5 порций')
    ], default=1)

    payment_type = RadioField('Тип оплаты', choices=[
        ('single', 'Разовая оплата (наличные/карта)'),
        ('subscription', 'Оплата абонементом (если есть активный)')
    ], validators=[DataRequired()])

    special_requests = TextAreaField('Особые пожелания/аллергены',
                                     validators=[Optional(), Length(max=500)],
                                     render_kw={"placeholder": "Укажите аллергены или особые пожелания"})

    order_date = DateField('Дата заказа', default=datetime.today,
                           validators=[DataRequired()])

    submit = SubmitField('Оформить заказ')


class FeedbackForm(FlaskForm):
    """Форма отзыва о блюде"""
    rating = SelectField('Оценка', choices=[
        (5, '5 - Отлично'),
        (4, '4 - Хорошо'),
        (3, '3 - Удовлетворительно'),
        (2, '2 - Плохо'),
        (1, '1 - Очень плохо')
    ], coerce=int, validators=[DataRequired()])

    comment = TextAreaField('Комментарий', validators=[
        Optional(),
        Length(max=1000, message='Комментарий не должен превышать 1000 символов')
    ], render_kw={"placeholder": "Поделитесь вашим мнением о блюде..."})

    submit = SubmitField('Оставить отзыв')


class ProfileForm(FlaskForm):
    """Форма редактирования профиля"""
    full_name = StringField('ФИО', validators=[
        DataRequired(message='Введите ваше имя'),
        Length(min=2, max=100, message='Имя должно быть от 2 до 100 символов')
    ], render_kw={"placeholder": "Иванов Иван Иванович"})

    email = StringField('Email', validators=[
        DataRequired(message='Введите email'),
        Email(message='Некорректный email адрес'),
        Length(max=120)
    ], render_kw={"disabled": True})  # Email нельзя менять

    class_group = StringField('Класс', validators=[
        DataRequired(message='Укажите ваш класс'),
        Length(min=1, max=10, message='Название класса должно быть от 1 до 10 символов')
    ], render_kw={"placeholder": "10А"})

    allergies = TextAreaField('Аллергии и особенности питания',
                              validators=[Optional(), Length(max=500)],
                              render_kw={
                                  "placeholder": "Перечислите аллергены через запятую (глютен, лактоза, орехи...)",
                                  "rows": 3
                              })

    preferences = SelectField('Предпочтения в питании', choices=[
        ('', 'Без предпочтений'),
        ('vegetarian', 'Вегетарианское'),
        ('vegan', 'Веганское'),
        ('halal', 'Халяль'),
        ('kosher', 'Кошерное'),
        ('no_meat', 'Без мяса'),
        ('no_fish', 'Без рыбы'),
        ('no_dairy', 'Без молочных продуктов')
    ], validators=[Optional()])

    avatar = FileField('Аватар', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Разрешены только изображения (JPG, PNG, GIF)!')
    ])

    submit = SubmitField('Сохранить изменения')