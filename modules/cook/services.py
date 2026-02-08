# modules/cook/services.py

from modules.core.database import db
from modules.core.models import Inventory, SupplyRequest


class CookServices:
    @staticmethod
    def check_and_create_supply_requests(cook_id):
        low_inventory = Inventory.query.filter(
            Inventory.current_quantity <= Inventory.min_quantity
        ).all()

        created_requests = 0

        for item in low_inventory:
            existing_request = SupplyRequest.query.filter_by(
                product_name=item.product_name,
                status='pending'
            ).first()

            if not existing_request:
                order_quantity = max(
                    int(item.min_quantity * 2 - item.current_quantity),
                    int(item.min_quantity)
                )

                urgency = 'critical' if item.current_quantity == 0 else 'high'

                supply_request = SupplyRequest(
                    cook_id=cook_id,
                    product_name=item.product_name,
                    quantity=order_quantity,
                    unit=item.unit,
                    urgency=urgency,
                    notes=f'Автоматическая заявка. Осталось: {item.current_quantity} {item.unit}. Минимум: {item.min_quantity} {item.unit}',
                    status='pending'
                )

                db.session.add(supply_request)
                created_requests += 1

        if created_requests > 0:
            db.session.commit()

        return created_requests

    @staticmethod
    def get_todays_order_stats():
        from datetime import datetime
        from modules.core.models import Order

        today = datetime.today().date()

        breakfast_orders = Order.query.filter_by(
            order_date=today,
            meal_time='breakfast'
        ).count()

        lunch_orders = Order.query.filter_by(
            order_date=today,
            meal_time='lunch'
        ).count()

        status_counts = db.session.query(
            Order.status,
            db.func.count(Order.id)
        ).filter_by(order_date=today).group_by(Order.status).all()

        return {
            'total': breakfast_orders + lunch_orders,
            'breakfast': breakfast_orders,
            'lunch': lunch_orders,
            'by_status': dict(status_counts)
        }

    @staticmethod
    def update_inventory_after_order(menu_item_id, quantity=1):
        pass