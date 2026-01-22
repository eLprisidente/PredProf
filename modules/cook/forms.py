from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileSize
from wtforms import StringField, IntegerField, SelectField, TextAreaField, SubmitField, DecimalField, BooleanField, \
    FloatField
from wtforms.validators import DataRequired, NumberRange, Length, Optional, ValidationError
from decimal import Decimal


class SupplyRequestForm(FlaskForm):
    """Форма заявки на поставку продуктов"""
    product_name = StringField('Название продукта', validators=[
        DataRequired(message='Название продукта обязательно'),
        Length(min=2, max=100, message='Название должно быть от 2 до 100 символов')
    ], render_kw={"placeholder": "Картофель, молоко, хлеб..."})

    quantity = FloatField('Количество', validators=[
        DataRequired(message='Укажите количество'),
        NumberRange(min=0.1, max=10000, message='Количество должно быть от 0.1 до 10000')
    ], default=1)

    unit = SelectField('Единица измерения', choices=[
        ('kg', 'Килограмм'),
        ('g', 'Грамм'),
        ('l', 'Литр'),
        ('ml', 'Миллилитр'),
        ('шт', 'Штуки'),
        ('уп', 'Упаковки'),
        ('банка', 'Банки'),
        ('пакет', 'Пакеты')
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
    current_quantity = FloatField('Текущее количество', validators=[
        DataRequired(message='Укажите количество'),
        NumberRange(min=0, max=100000, message='Количество должно быть от 0 до 100000')
    ])

    min_quantity = FloatField('Минимальный запас', validators=[
        DataRequired(message='Укажите минимальный запас'),
        NumberRange(min=0, max=10000, message='Минимальный запас должен быть от 0 до 10000')
    ], default=10)

    notes = TextAreaField('Примечания', validators=[Optional(), Length(max=200)],
                          render_kw={"placeholder": "Например: 'Поступила новая поставка'"})

    submit = SubmitField('Обновить')


class InventoryItemForm(FlaskForm):
    """Форма добавления нового продукта в инвентарь"""
    product_name = StringField('Название продукта', validators=[
        DataRequired(message='Название продукта обязательно'),
        Length(min=2, max=100, message='Название должно быть от 2 до 100 символов')
    ])

    current_quantity = FloatField('Начальное количество', validators=[
        DataRequired(message='Укажите количество'),
        NumberRange(min=0, max=100000, message='Количество должно быть от 0 до 100000')
    ], default=0)

    min_quantity = FloatField('Минимальный запас', validators=[
        DataRequired(message='Укажите минимальный запас'),
        NumberRange(min=0, max=10000, message='Минимальный запас должен быть от 0 до 10000')
    ], default=10)

    unit = SelectField('Единица измерения', choices=[
        ('kg', 'Килограмм'),
        ('g', 'Грамм'),
        ('l', 'Литр'),
        ('ml', 'Миллилитр'),
        ('шт', 'Штуки'),
        ('уп', 'Упаковки'),
        ('банка', 'Банки'),
        ('пакет', 'Пакеты')
    ], validators=[DataRequired()])

    category = SelectField('Категория', choices=[
        ('vegetables', 'Овощи'),
        ('fruits', 'Фрукты'),
        ('meat', 'Мясо'),
        ('fish', 'Рыба'),
        ('dairy', 'Молочные продукты'),
        ('bakery', 'Выпечка'),
        ('groceries', 'Бакалея'),
        ('drinks', 'Напитки'),
        ('spices', 'Специи'),
        ('other', 'Другое')
    ], validators=[DataRequired()])

    submit = SubmitField('Добавить продукт')


class MenuItemForm(FlaskForm):
    """Форма добавления/редактирования блюда в меню"""
    name = StringField('Название блюда', validators=[
        DataRequired(message='Название блюда обязательно'),
        Length(min=2, max=100, message='Название должно быть от 2 до 100 символов')
    ], render_kw={"placeholder": "Куриный суп, гречневая каша..."})

    description = TextAreaField('Описание', validators=[
        DataRequired(message='Описание обязательно'),
        Length(min=10, max=500, message='Описание должно быть от 10 до 500 символов')
    ], render_kw={"placeholder": "Вкусное и полезное блюдо..."})

    price = DecimalField('Цена (₽)', places=2, validators=[
        DataRequired(message='Укажите цену'),
        NumberRange(min=0, max=10000, message='Цена должна быть от 0 до 10000')
    ], render_kw={"placeholder": "100.00"})

    category = SelectField('Категория', choices=[
        ('breakfast', 'Завтрак'),
        ('lunch', 'Обед'),
        ('snack', 'Перекус')
    ], validators=[DataRequired()])

    meal_type = SelectField('Тип питания', choices=[
        ('regular', 'Обычное'),
        ('vegetarian', 'Вегетарианское'),
        ('meat', 'Мясное'),
        ('fish', 'Рыбное'),
        ('vegan', 'Веганское'),
        ('dairy', 'Молочное'),
        ('dietary', 'Диетическое')
    ], validators=[DataRequired()])

    allergens = TextAreaField('Аллергены', validators=[Optional(), Length(max=300)],
                              render_kw={"placeholder": "Глютен, лактоза, орехи, яйца..."})

    image = FileField('Изображение блюда', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'],
                    'Разрешены только изображения (jpg, png, gif, webp)'),
        FileSize(max_size=5 * 1024 * 1024,
                 message='Максимальный размер файла - 5MB')
    ], render_kw={"accept": ".jpg,.jpeg,.png,.gif,.webp"})

    available = BooleanField('Доступно для заказа', default=True)

    submit = SubmitField('Сохранить блюдо')

    def validate_price(self, field):
        if field.data and field.data < 0:
            raise ValidationError('Цена не может быть отрицательной')

    def validate_image(self, field):
        if field.data:
            # Проверка типа файла
            filename = field.data.filename
            if filename:
                allowed_extensions = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
                ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
                if ext not in allowed_extensions:
                    raise ValidationError('Недопустимый формат файла. Разрешены: jpg, png, gif, webp')
