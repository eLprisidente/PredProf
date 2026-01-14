from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, TextAreaField, SubmitField, DecimalField, BooleanField
from wtforms.validators import DataRequired, NumberRange, Length, Optional
from decimal import Decimal


class SupplyRequestForm(FlaskForm):
    """Форма заявки на поставку продуктов"""
    product_name = StringField('Название продукта', validators=[
        DataRequired(message='Название продукта обязательно'),
        Length(min=2, max=100, message='Название должно быть от 2 до 100 символов')
    ], render_kw={"placeholder": "Картофель, молоко, хлеб..."})

    quantity = IntegerField('Количество', validators=[
        DataRequired(message='Укажите количество'),
        NumberRange(min=1, max=10000, message='Количество должно быть от 1 до 10000')
    ], default=1)

    unit = SelectField('Единица измерения', choices=[
        ('kg', 'Килограмм'),
        ('g', 'Грамм'),
        ('l', 'Литр'),
        ('ml', 'Миллилитр'),
        ('pieces', 'Штуки'),
        ('packages', 'Упаковки')
    ], validators=[DataRequired()])

    urgency = SelectField('Срочность', choices=[
        ('low', 'Низкая'),
        ('normal', 'Обычная'),
        ('high', 'Высокая'),
        ('critical', 'Критическая')
    ], default='normal')

    notes = TextAreaField('Примечания', validators=[Optional(), Length(max=500)],
                          render_kw={"placeholder": "Дополнительная информация о заявке..."})

    submit = SubmitField('Создать заявку')


class InventoryUpdateForm(FlaskForm):
    """Форма обновления инвентаря"""
    current_quantity = IntegerField('Текущее количество', validators=[
        DataRequired(),
        NumberRange(min=0, max=100000)
    ])

    min_quantity = IntegerField('Минимальный запас', validators=[
        DataRequired(),
        NumberRange(min=0, max=10000)
    ], default=10)

    notes = TextAreaField('Примечания', validators=[Optional(), Length(max=200)],
                          render_kw={"placeholder": "Например: 'Поступила новая поставка'"})

    submit = SubmitField('Обновить')


class MenuItemForm(FlaskForm):
    """Форма добавления/редактирования блюда в меню"""
    name = StringField('Название блюда', validators=[
        DataRequired(),
        Length(min=2, max=100)
    ])

    description = TextAreaField('Описание', validators=[
        DataRequired(),
        Length(min=10, max=500)
    ])

    price = DecimalField('Цена', places=2, validators=[
        DataRequired(),
        NumberRange(min=0, max=10000)
    ])

    category = SelectField('Категория', choices=[
        ('breakfast', 'Завтрак'),
        ('lunch', 'Обед'),
        ('snack', 'Перекус')
    ], validators=[DataRequired()])

    meal_type = SelectField('Тип блюда', choices=[
        ('vegetarian', 'Вегетарианское'),
        ('meat', 'Мясное'),
        ('fish', 'Рыбное'),
        ('vegan', 'Веганское'),
        ('dairy', 'Молочное')
    ], validators=[DataRequired()])

    allergens = TextAreaField('Аллергены', validators=[Optional(), Length(max=300)],
                              render_kw={"placeholder": "Глютен, лактоза, орехи..."})

    available = BooleanField('Доступно для заказа', default=True)

    submit = SubmitField('Сохранить')