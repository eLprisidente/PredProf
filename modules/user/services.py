from datetime import datetime, date, timedelta
from modules.core.database import db
from modules.core.models import Subscription, Order, Transaction


class SubscriptionService:

    DAY_PRICE = 150.0  # Цена за один день

    @staticmethod
    def get_user_subscriptions(user_id):
        from modules.core.models import Subscription

        subscriptions = Subscription.query.filter_by(
            user_id=user_id
        ).order_by(
            Subscription.created_at.desc()
        ).all()

        for sub in subscriptions:
            if sub.is_active and sub.end_date < datetime.utcnow():
                sub.is_active = False
        if subscriptions:
            db.session.commit()

        return subscriptions

    @staticmethod
    def get_active_subscription(user_id):
        from modules.core.models import Subscription

        now = datetime.utcnow()

        subscription = Subscription.query.filter(
            Subscription.user_id == user_id,
            Subscription.is_active == True,
            Subscription.end_date > now
        ).first()

        return subscription

    @staticmethod
    def purchase_subscription(user, days):
        from modules.core.models import Subscription, Transaction

        if days < 1 or days > 365:
            return False, "Можно купить абонемент от 1 до 365 дней", None

        price = days * SubscriptionService.DAY_PRICE

        if user.balance < price:
            return False, f"Недостаточно средств. Нужно {price} ₽, на балансе {user.balance:.2f} ₽", None

        old_subscriptions = Subscription.query.filter(
            Subscription.user_id == user.id,
            Subscription.is_active == True
        ).all()

        for old_sub in old_subscriptions:
            old_sub.is_active = False

        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=days)

        subscription = Subscription(
            user_id=user.id,
            days=days,
            start_date=start_date,
            end_date=end_date,
            price=price,
            is_active=True
        )

        user.balance -= price

        transaction = Transaction(
            user_id=user.id,
            amount=-price,
            transaction_type='subscription',
            status='completed',
            description=f'Покупка абонемента на {days} дней'
        )

        db.session.add(subscription)
        db.session.add(transaction)
        db.session.commit()

        return True, f"Абонемент на {days} дней успешно приобретен! Действует до {end_date.strftime('%d.%m.%Y')}", subscription

    @staticmethod
    def use_subscription_for_order(order_id, subscription_id):
        from modules.core.models import Order, Subscription

        order = Order.query.get(order_id)
        subscription = Subscription.query.get(subscription_id)

        if not order or not subscription:
            return False, "Заказ или абонемент не найден"

        if not subscription.is_active:
            return False, "Абонемент не активен"

        now = datetime.utcnow()
        if subscription.end_date < now:
            subscription.is_active = False
            db.session.commit()
            return False, "Срок действия абонемента истек"

        order.payment_type = 'subscription'
        order.payment_status = 'paid'
        order.subscription_id = subscription.id

        db.session.commit()
        return True, "Оплата абонементом прошла успешно"

    @staticmethod
    def check_subscription_usage(user_id, start_date=None, end_date=None):
        from modules.core.models import Order

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
        from modules.core.models import Subscription, Transaction

        subscription = Subscription.query.get(subscription_id)

        if not subscription:
            return False, "Абонемент не найден"

        now = datetime.utcnow()
        if subscription.start_date < now:
            return False, "Нельзя отменить начавшийся абонемент"

        user = subscription.user
        user.balance += subscription.price

        transaction = Transaction(
            user_id=user.id,
            amount=subscription.price,
            transaction_type='refund',
            status='completed',
            description=f'Отмена абонемента #{subscription.id}'
        )

        db.session.delete(subscription)
        db.session.add(transaction)
        db.session.commit()

        return True, "Абонемент отменен, средства возвращены на баланс"


class PaymentService:

    @staticmethod
    def get_payment_options(user_id):
        options = ['balance']

        active_subscription = SubscriptionService.get_active_subscription(user_id)
        if active_subscription:
            options.append('subscription')

        return options
