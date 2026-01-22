from datetime import datetime
from flask_login import UserMixin
from modules.core.database import db


class User(UserMixin, db.Model):
    """Модель пользователя"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'student', 'cook', 'admin'
    full_name = db.Column(db.String(100))
    class_group = db.Column(db.String(50))  # Только для учеников
    allergies = db.Column(db.Text, default='')  # JSON или текст с аллергенами
    preferences = db.Column(db.String(50), default='')  # Новое поле: предпочтения в питании
    avatar_url = db.Column(db.String(255))  # Новое поле: путь к аватару
    balance = db.Column(db.Float, default=0.0)  # Новое поле: баланс счета
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

    def __repr__(self):
        return f'<MenuItem {self.name} ({self.category})>'


class Subscription(db.Model):
    """Модель абонемента"""
    __tablename__ = 'subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subscription_type = db.Column(db.String(20))  # 'weekly', 'monthly'
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    price = db.Column(db.Float, nullable=False)
    meals_remaining = db.Column(db.Integer, default=0)  # Осталось приемов пищи
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Связи
    user = db.relationship('User', backref='subscriptions')

    def __repr__(self):
        return f'<Subscription {self.id} for User {self.user_id}>'


class Order(db.Model):
    """Модель заказа"""
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscriptions.id'), nullable=True)
    order_date = db.Column(db.Date, default=datetime.utcnow().date, nullable=False)
    meal_time = db.Column(db.String(20), nullable=False)  # 'breakfast', 'lunch'
    quantity = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), default='ordered')  # 'ordered', 'preparing', 'ready', 'received', 'cancelled'
    payment_type = db.Column(db.String(20))  # 'single', 'subscription'
    payment_status = db.Column(db.String(20), default='pending')  # 'pending', 'paid', 'failed', 'refunded'
    special_requests = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    total_price = db.Column(db.Numeric(10, 2), default=0)

    # Связи
    user = db.relationship('User', backref='orders')
    menu_item = db.relationship('MenuItem', backref='orders')
    subscription = db.relationship('Subscription', backref='orders')

    def __repr__(self):
        return f'<Order {self.id} by User {self.user_id}>'

    @property
    def total_price(self):
        if self.menu_item and self.quantity:
            return self.menu_item.price * self.quantity
        return 0


class Feedback(db.Model):
    """Модель отзыва"""
    __tablename__ = 'feedbacks'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    rating = db.Column(db.Integer)  # 1-5
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Feedback {self.id} ({self.rating} stars)>'


class SupplyRequest(db.Model):
    """Модель заявки на поставку"""
    __tablename__ = 'supply_requests'

    id = db.Column(db.Integer, primary_key=True)
    cook_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit = db.Column(db.String(20))  # 'kg', 'liters', 'pieces', 'packages'
    urgency = db.Column(db.String(20), default='normal')  # 'low', 'normal', 'high', 'critical'
    status = db.Column(db.String(20), default='pending')  # 'pending', 'approved', 'rejected', 'delivered'
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approval_date = db.Column(db.DateTime, nullable=True)

    # Связи
    cook = db.relationship('User', foreign_keys=[cook_id])
    approver = db.relationship('User', foreign_keys=[approved_by])

    def __repr__(self):
        return f'<SupplyRequest {self.id} for {self.product_name}>'


class Inventory(db.Model):
    """Модель инвентаря"""
    __tablename__ = 'inventory'

    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(100), nullable=False, unique=True)
    current_quantity = db.Column(db.Float, default=0)
    min_quantity = db.Column(db.Float, default=10)  # Минимальный запас для заказа
    unit = db.Column(db.String(20))
    category = db.Column(db.String(50))  # 'vegetables', 'meat', 'dairy', etc.
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Inventory {self.product_name}: {self.current_quantity} {self.unit}>'