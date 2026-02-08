from datetime import datetime, date
from flask_login import UserMixin
from modules.core.database import db
from datetime import datetime, timedelta


class User(UserMixin, db.Model):
    """Модель пользователя"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'student', 'cook', 'admin'
    full_name = db.Column(db.String(100))
    class_group = db.Column(db.String(50), nullable=True)  # Теперь nullable=True!
    allergies = db.Column(db.Text, default='')
    preferences = db.Column(db.String(50), default='')
    avatar_url = db.Column(db.String(255))
    balance = db.Column(db.Float, default=0.0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<User {self.email} ({self.role})>'


class MenuItem(db.Model):
    """Модель блюда в меню"""
    __tablename__ = 'menu_items'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50))  # 'breakfast', 'lunch', 'snack'
    meal_type = db.Column(db.String(20))  # 'vegetarian', 'meat', 'fish', etc.
    allergens = db.Column(db.Text)  # JSON список аллергенов
    available = db.Column(db.Boolean, default=True)
    image_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False)  # Флаг мягкого удаления

    def __repr__(self):
        return f'<MenuItem {self.name} ({self.category})>'


class Subscription(db.Model):
    """Модель абонемента на питание"""
    __tablename__ = 'subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    days = db.Column(db.Integer, nullable=False)  # Количество дней
    price = db.Column(db.Float, nullable=False)  # Сумма оплаты
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Связи с каскадным удалением
    user = db.relationship('User', backref=db.backref('subscriptions', lazy=True, cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<Subscription {self.id} for user {self.user_id}>'

    @property
    def days_remaining(self):
        """Количество оставшихся дней"""
        if not self.is_active:
            return 0

        now = datetime.utcnow()

        if self.end_date < now:
            return 0

        delta = self.end_date - now
        days = delta.days

        if delta.seconds > 0:
            days += 1

        return max(0, days)

    @property
    def status_text(self):
        """Текстовый статус абонемента"""
        if not self.is_active:
            return "Неактивен"

        days = self.days_remaining
        if days == 0:
            return "Истек"
        elif days == 1:
            return "Истекает сегодня"
        elif days <= 7:
            return f"Истекает через {days} дней"
        else:
            return f"Активен ({days} дней)"


class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id', ondelete='SET NULL'), nullable=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscriptions.id', ondelete='SET NULL'), nullable=True)
    order_date = db.Column(db.Date, default=date.today, nullable=False)
    meal_time = db.Column(db.String(20), nullable=False)
    quantity = db.Column(db.Integer, default=1)

    # Добавляем физическую колонку для total_price
    total_price = db.Column(db.Float, default=0.0, nullable=False)

    status = db.Column(db.String(20), default='pending')

    # Статус оплаты
    payment_type = db.Column(db.String(20), default='single')
    payment_status = db.Column(db.String(20), default='pending')
    refunded = db.Column(db.Boolean, default=False)
    refund_amount = db.Column(db.Float, default=0.0)
    refund_date = db.Column(db.DateTime, nullable=True)

    special_requests = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи с каскадным удалением
    user = db.relationship('User', backref=db.backref('orders', lazy=True, cascade='all, delete-orphan'))
    menu_item = db.relationship('MenuItem', backref=db.backref('orders', lazy=True, cascade='all, delete-orphan'))
    subscription = db.relationship('Subscription',
                                   backref=db.backref('orders', lazy=True, cascade='all, delete-orphan'))

    def __init__(self, **kwargs):
        # Убираем total_price из kwargs, чтобы не передавать в SQLAlchemy
        total_price = kwargs.pop('total_price', None)
        super().__init__(**kwargs)

        # Устанавливаем total_price после инициализации
        if total_price is not None:
            self._total_price = total_price

    def __repr__(self):
        return f'<Order {self.id} by User {self.user_id}>'

    # Property для вычисления цены на лету (используется только если не задана явно)
    @property
    def calculated_price(self):
        if self.menu_item and self.quantity:
            return self.menu_item.price * self.quantity
        return 0

    @property
    def display_total(self):
        """Форматированная сумма для отображения"""
        if self.total_price and self.total_price > 0:
            price = self.total_price
        else:
            price = self.calculated_price

        return f"{price:.2f} ₽"

    @property
    def status_display(self):
        status_map = {
            'pending': 'Ожидает подтверждения',
            'preparing': 'В работе',
            'ready': 'Готов к выдаче',
            'received': 'Получен',
            'cancelled': 'Отменен'
        }
        return status_map.get(self.status, self.status)

    @property
    def payment_status_display(self):
        status_map = {
            'pending': 'Ожидает оплаты',
            'paid': 'Оплачено',
            'failed': 'Ошибка оплаты',
            'refunded': 'Возврат средств'
        }
        return status_map.get(self.payment_status, self.payment_status)


class Feedback(db.Model):
    __tablename__ = 'feedbacks'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id', ondelete='SET NULL'), nullable=True)
    rating = db.Column(db.Integer)  # 1-5
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Связи с каскадным удалением
    user = db.relationship('User', backref=db.backref('feedbacks', lazy=True, cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<Feedback {self.id} ({self.rating} stars)>'


class SupplyRequest(db.Model):
    __tablename__ = 'supply_requests'

    id = db.Column(db.Integer, primary_key=True)
    cook_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    product_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    urgency = db.Column(db.String(20), default='normal')
    notes = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected, cancelled
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Связи с каскадным удалением
    cook = db.relationship('User', foreign_keys=[cook_id],
                           backref=db.backref('supply_requests_cook', lazy=True))
    approver = db.relationship('User', foreign_keys=[approved_by],
                               backref=db.backref('supply_requests_approver', lazy=True))

    def __repr__(self):
        return f'<SupplyRequest {self.id}: {self.product_name}>'


class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id', ondelete='SET NULL'), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # 'deposit', 'payment', 'refund'
    status = db.Column(db.String(20), default='pending')  # 'pending', 'completed', 'failed'
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Связи с каскадным удалением
    user = db.relationship('User', backref=db.backref('transactions', lazy=True, cascade='all, delete-orphan'))
    order = db.relationship('Order', backref=db.backref('transactions', lazy=True, cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<Transaction {self.id}: {self.transaction_type} {self.amount}>'
