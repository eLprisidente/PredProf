from datetime import datetime, timedelta
from modules.core.database import db
from modules.core.models import Order, Subscription


class PaymentService:
    """Сервис для обработки оплат"""

    @staticmethod
    def process_single_payment(order_id):
        """Обработка разовой оплаты"""
        order = Order.query.get(order_id)
        if not order:
            return False, "Заказ не найден"

        if order.payment_status == 'paid':
            return False, "Заказ уже оплачен"

        order.payment_status = 'paid'
        order.status = 'ordered'
        db.session.commit()

        return True, "Оплата прошла успешно"

    @staticmethod
    def process_subscription_payment(user_id, subscription_type):
        """Оформление абонемента"""
        from modules.core.models import User

        user = User.query.get(user_id)
        if not user:
            return False, "Пользователь не найден"

        prices = {
            'weekly': 1500.00,
            'monthly': 5000.00
        }

        if subscription_type not in prices:
            return False, "Неверный тип абонемента"

        meals_count = {
            'weekly': 10,
            'monthly': 40
        }

        start_date = datetime.today().date()

        if subscription_type == 'weekly':
            end_date = start_date + timedelta(days=7)
        else:  # monthly
            end_date = start_date + timedelta(days=30)

        subscription = Subscription(
            user_id=user_id,
            subscription_type=subscription_type,
            start_date=start_date,
            end_date=end_date,
            price=prices[subscription_type],
            meals_remaining=meals_count[subscription_type],
            is_active=True
        )

        db.session.add(subscription)
        db.session.commit()

        return True, subscription.id

    @staticmethod
    def use_subscription_for_order(order_id, subscription_id):
        """Использовать абонемент для оплаты заказа"""
        order = Order.query.get(order_id)
        subscription = Subscription.query.get(subscription_id)

        if not order or not subscription:
            return False, "Заказ или абонемент не найден"

        if not subscription.is_active:
            return False, "Абонемент не активен"

        if datetime.today().date() > subscription.end_date:
            subscription.is_active = False
            db.session.commit()
            return False, "Срок действия абонемента истек"

        if subscription.meals_remaining <= 0:
            subscription.is_active = False
            db.session.commit()
            return False, "Лимит приемов пищи исчерпан"

        subscription.meals_remaining -= order.quantity
        order.payment_type = 'subscription'
        order.payment_status = 'paid'
        order.subscription_id = subscription.id

        if subscription.meals_remaining <= 0:
            subscription.is_active = False

        db.session.commit()
        return True, "Оплата абонементом прошла успешно"

    @staticmethod
    def check_subscription_status(user_id):
        """Проверка статуса абонемента пользователя"""
        active_subscription = Subscription.query.filter_by(
            user_id=user_id,
            is_active=True
        ).first()

        if not active_subscription:
            return None

        if datetime.today().date() > active_subscription.end_date:
            active_subscription.is_active = False
            db.session.commit()
            return None

        return active_subscription