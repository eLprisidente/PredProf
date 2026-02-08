from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, SelectField, IntegerField, TextAreaField, SubmitField, DateField, RadioField, DecimalField
from wtforms.validators import DataRequired, NumberRange, Optional, Length, Email
from datetime import datetime

class BalanceForm(FlaskForm):
    amount = DecimalField('Сумма пополнения', places=2, validators=[
        DataRequired(message='Введите сумму пополнения'),
        NumberRange(min=10, max=10000, message='Сумма должна быть от 10 до 10 000 ₽')
    ], render_kw={"placeholder": "100.00", "step": "10"})
    submit = SubmitField('Пополнить баланс')

class OrderForm(FlaskForm):
    menu_item_id = SelectField('Блюдо', coerce=int, validators=[Optional()])
    meal_time = SelectField('Время приема пищи', choices=[
        ('breakfast', 'Завтрак'),
        ('lunch', 'Обед')
    ], validators=[Optional()])
    quantity = IntegerField('Количество', validators=[
        Optional(),
        NumberRange(min=1, max=5, message='Можно заказать от 1 до 5 порций')
    ], default=1)
    payment_type = RadioField('Тип оплаты', choices=[
        ('single', 'Разовая оплата (наличные/карта)'),
        ('subscription', 'Оплата абонементом (если есть активный)')
    ], validators=[Optional()])
    special_requests = TextAreaField('Особые пожелания/аллергены',
                                     validators=[Optional(), Length(max=500)],
                                     render_kw={"placeholder": "Укажите аллергены или особые пожелания"})
    order_date = DateField('Дата заказа', default=datetime.today,
                           validators=[Optional()])
    submit = SubmitField('Оформить заказ')

class FeedbackForm(FlaskForm):
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
    full_name = StringField('ФИО', validators=[
        DataRequired(message='Введите ваше имя'),
        Length(min=2, max=100, message='Имя должно быть от 2 до 100 символов')
    ], render_kw={"placeholder": "Иванов Иван Иванович"})
    email = StringField('Email', validators=[
        DataRequired(message='Введите email'),
        Email(message='Некорректный email адрес'),
        Length(max=120)
    ], render_kw={"disabled": True})
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


# Добавьте в конец файла:
class SubscriptionForm(FlaskForm):
    days = IntegerField('Количество дней',
                        validators=[
                            DataRequired(message='Укажите количество дней'),
                            NumberRange(min=1, max=365, message='Можно купить от 1 до 365 дней')
                        ],
                        default=30,
                        render_kw={"placeholder": "Введите количество дней"})

    submit = SubmitField('Купить абонемент')
