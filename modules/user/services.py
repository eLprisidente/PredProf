from datetime import datetime, date, timedelta
from modules.core.database import db
from modules.core.models import Subscription, Order, Transaction


class SubscriptionService:
    """Сервис для работы с абонементами"""

    @staticmethod
    def get_user_subscriptions(user_id):
        """Получить все абонементы пользователя"""
        return Subscription.query.filter_by(
            user_id=user_id
        ).order_by(
            Subscription.created_at.desc()
        ).all()

    @staticmethod
    def get_active_subscription(user_id):
        """Получить активный абонемент пользователя"""
        today = date.today()

        # Ищем активный абонемент, который еще не истек
        subscription = Subscription.query.filter(
            Subscription.user_id == user_id,
            Subscription.is_active == True,
            Subscription.end_date >= today
        ).first()

        # Если абонемент истек, деактивируем его
        if subscription and subscription.end_date < today:
            subscription.is_active = False
            db.session.commit()
            return None

        return subscription

    @staticmethod
    def purchase_subscription(user, subscription_type):
        """Покупка абонемента"""
        # Цены и настройки абонементов
        subscription_configs = {
            'weekly': {
                'name': 'Недельный',
                'price': 1500.00,
                'days': 7,
                'meals': 10
            },
            'monthly': {
                'name': 'Месячный',
                'price': 5000.00,
                'days': 30,
                'meals': 40
            }
        }

        if subscription_type not in subscription_configs:
            return False, "Неверный тип абонемента"

        config = subscription_configs[subscription_type]

        # Проверяем баланс пользователя
        if user.balance < config['price']:
            shortage = config['price'] - user.balance
            return False, f"Недостаточно средств. Нужно {config['price']} ₽, на балансе {user.balance} ₽"

        # Проверяем, нет ли уже активного абонемента
        active_subscription = SubscriptionService.get_active_subscription(user.id)
        if active_subscription:
            return False, f"У вас уже есть активный абонемент (действует до {active_subscription.end_date.strftime('%d.%m.%Y')})"

        # Создаем абонемент
        start_date = date.today()
        end_date = start_date + timedelta(days=config['days'])

        subscription = Subscription(
            user_id=user.id,
            subscription_type=subscription_type,
            start_date=start_date,
            end_date=end_date,
            price=config['price'],
            meals_remaining=config['meals'],
            is_active=True
        )

        # Списание средств с баланса
        user.balance -= config['price']

        # Создаем транзакцию
        transaction = Transaction(
            user_id=user.id,
            amount=config['price'],
            transaction_type='subscription',
            status='completed',
            description=f'Покупка {config["name"].lower()} абонемента'
        )

        db.session.add(subscription)
        db.session.add(transaction)
        db.session.commit()

        return True, subscription

    @staticmethod
    def use_subscription_for_order(order_id, subscription_id):
        """Использовать абонемент для оплаты заказа"""
        from modules.core.models import Order, Subscription

        order = Order.query.get(order_id)
        subscription = Subscription.query.get(subscription_id)

        if not order or not subscription:
            return False, "Заказ или абонемент не найден"

        # Проверяем, что абонемент активен
        if not subscription.is_active:
            return False, "Абонемент не активен"

        # Проверяем срок действия
        today = date.today()
        if subscription.end_date < today:
            subscription.is_active = False
            db.session.commit()
            return False, "Срок действия абонемента истек"

        # Проверяем остаток приемов пищи
        if subscription.meals_remaining < order.quantity:
            return False, f"Недостаточно приемов пищи в абонементе. Осталось: {subscription.meals_remaining}"

        # Используем абонемент
        subscription.meals_remaining -= order.quantity
        order.payment_type = 'subscription'
        order.payment_status = 'paid'
        order.subscription_id = subscription.id

        # Если приемы пищи закончились, деактивируем абонемент
        if subscription.meals_remaining <= 0:
            subscription.is_active = False

        db.session.commit()
        return True, "Оплата абонементом прошла успешно"

    @staticmethod
    def check_subscription_usage(user_id, start_date=None, end_date=None):
        """Проверить использование абонемента за период"""
        query = Order.query.filter(
            Order.user_id == user_id,
            Order.payment_type == 'subscription',
            Order.payment_status == 'paid'
        )

        if start_date:
            query = query.filter(Order.order_date >= start_date)
        if end_date:
            query = query.filter(Order.order_date <= end_date)

        orders = query.all()

        total_used = sum(order.quantity for order in orders)
        total_cost = sum(order.menu_item.price * order.quantity for order in orders if order.menu_item)

        return {
            'orders_count': len(orders),
            'meals_used': total_used,
            'total_cost': total_cost,
            'orders': orders
        }

    @staticmethod
    def cancel_subscription(subscription_id):
        """Отмена абонемента с возвратом средств"""
        subscription = Subscription.query.get(subscription_id)

        if not subscription:
            return False, "Абонемент не найден"

        # Проверяем, можно ли отменить
        today = date.today()
        if subscription.start_date < today:
            return False, "Нельзя отменить начавшийся абонемент"

        # Возвращаем средства
        user = subscription.user
        user.balance += subscription.price

        # Создаем транзакцию возврата
        transaction = Transaction(
            user_id=user.id,
            amount=subscription.price,
            transaction_type='refund',
            status='completed',
            description=f'Отмена абонемента #{subscription.id}'
        )

        # Удаляем абонемент
        db.session.delete(subscription)
        db.session.add(transaction)
        db.session.commit()

        return True, "Абонемент отменен, средства возвращены на баланс"


class PaymentService:
    """Сервис для обработки оплат"""

    @staticmethod
    def get_payment_options(user_id):
        """Получить доступные способы оплаты для пользователя"""
        options = ['balance']  # Всегда доступна оплата с баланса

        # Проверяем наличие активного абонемента
        active_subscription = SubscriptionService.get_active_subscription(user_id)
        if active_subscription:
            options.append('subscription')

        return options
