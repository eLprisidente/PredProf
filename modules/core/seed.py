from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from modules.core.database import db
from modules.core.models import User, MenuItem, Inventory, Subscription, Order, Feedback, SupplyRequest


def seed_database():

    if User.query.count() == 0:

        admin = User(
            email='admin@school.ru',
            password=generate_password_hash('admin123', method='pbkdf2:sha256'),
            role='admin',
            full_name='Администратор Системы',
            is_active=True
        )

        cook = User(
            email='cook@school.ru',
            password=generate_password_hash('cook123', method='pbkdf2:sha256'),
            role='cook',
            full_name='Иванов Иван Иванович',
            is_active=True
        )

        students = [
            User(
                email='student@school.ru',
                password=generate_password_hash('student123', method='pbkdf2:sha256'),
                role='student',
                full_name='Петров Петр Петрович',
                class_group='11Л',
                allergies='Глютен, лактоза',
                is_active=True
            )
        ]

        db.session.add(admin)
        db.session.add(cook)
        for student in students:
            db.session.add(student)

        db.session.commit()

    if MenuItem.query.count() == 0:

        menu_items = [
            MenuItem(
                name='Овсяная каша с ягодами',
                description='Полезная овсянка со свежими ягодами и медом',
                price=120.0,
                category='breakfast',
                meal_type='vegetarian',
                allergens='глютен, лактоза',
                available=True
            ),
            MenuItem(
                name='Омлет с сыром и ветчиной',
                description='Пышный омлет с сыром, ветчиной и зеленью',
                price=150.0,
                category='breakfast',
                meal_type='meat',
                allergens='яйца, лактоза',
                available=True
            ),
            MenuItem(
                name='Блины с вареньем',
                description='Тонкие блины с домашним клубничным вареньем',
                price=130.0,
                category='breakfast',
                meal_type='vegetarian',
                allergens='глютен, яйца',
                available=True
            ),
            MenuItem(
                name='Творожная запеканка',
                description='Нежная творожная запеканка с изюмом',
                price=140.0,
                category='breakfast',
                meal_type='dairy',
                allergens='лактоза, яйца',
                available=True
            ),

            MenuItem(
                name='Куриный суп с лапшой',
                description='Наваристый суп с курицей, овощами и домашней лапшой',
                price=180.0,
                category='lunch',
                meal_type='meat',
                allergens='глютен',
                available=True
            ),
            MenuItem(
                name='Гречка с грибами',
                description='Гречневая каша с тушеными грибами и луком',
                price=160.0,
                category='lunch',
                meal_type='vegetarian',
                allergens='',
                available=True
            ),
            MenuItem(
                name='Рыбные котлеты с картофельным пюре',
                description='Нежные рыбные котлеты с картофельным пюре и зеленым горошком',
                price=200.0,
                category='lunch',
                meal_type='fish',
                allergens='рыба, молоко',
                available=True
            ),
            MenuItem(
                name='Спагетти болоньезе',
                description='Итальянские спагетти с мясным соусом болоньезе',
                price=190.0,
                category='lunch',
                meal_type='meat',
                allergens='глютен',
                available=True
            ),
            MenuItem(
                name='Овощное рагу',
                description='Тушеные овощи с картофелем и специями',
                price=170.0,
                category='lunch',
                meal_type='vegan',
                allergens='',
                available=True
            ),
            MenuItem(
                name='Котлета по-киевски с рисом',
                description='Куриная котлета с масляно-зеленым соусом, подается с рассыпчатым рисом',
                price=220.0,
                category='lunch',
                meal_type='meat',
                allergens='яйца, глютен',
                available=True
            )
        ]

        for item in menu_items:
            db.session.add(item)

        db.session.commit()

    if Inventory.query.count() == 0:

        inventory_items = [
            Inventory(product_name='Картофель', current_quantity=50, min_quantity=10, unit='кг', category='овощи'),
            Inventory(product_name='Морковь', current_quantity=20, min_quantity=5, unit='кг', category='овощи'),
            Inventory(product_name='Лук', current_quantity=15, min_quantity=3, unit='кг', category='овощи'),
            Inventory(product_name='Капуста', current_quantity=10, min_quantity=2, unit='кг', category='овощи'),
            Inventory(product_name='Курица', current_quantity=30, min_quantity=10, unit='кг', category='мясо'),
            Inventory(product_name='Говядина', current_quantity=15, min_quantity=5, unit='кг', category='мясо'),
            Inventory(product_name='Молоко', current_quantity=40, min_quantity=20, unit='л', category='молочные'),
            Inventory(product_name='Сыр', current_quantity=8, min_quantity=2, unit='кг', category='молочные'),
            Inventory(product_name='Яйца', current_quantity=200, min_quantity=50, unit='шт', category='молочные'),
            Inventory(product_name='Мука', current_quantity=25, min_quantity=5, unit='кг', category='бакалея'),
            Inventory(product_name='Сахар', current_quantity=15, min_quantity=3, unit='кг', category='бакалея'),
            Inventory(product_name='Рис', current_quantity=20, min_quantity=5, unit='кг', category='бакалея'),
            Inventory(product_name='Гречка', current_quantity=12, min_quantity=3, unit='кг', category='бакалея'),
            Inventory(product_name='Подсолнечное масло', current_quantity=10, min_quantity=2, unit='л',
                      category='бакалея'),
            Inventory(product_name='Томатная паста', current_quantity=8, min_quantity=1, unit='кг', category='бакалея'),
            Inventory(product_name='Рыба', current_quantity=12, min_quantity=3, unit='кг', category='рыба'),
        ]

        for item in inventory_items:
            db.session.add(item)

        db.session.commit()

    students = User.query.filter_by(role='student').all()
    if students and Subscription.query.count() == 0:

        for i, student in enumerate(students):
            subscription_type = 'weekly' if i % 2 == 0 else 'monthly'
            start_date = datetime.today().date()
            end_date = start_date + timedelta(days=7 if subscription_type == 'weekly' else 30)
            meals_count = 10 if subscription_type == 'weekly' else 40
            price = 1500.00 if subscription_type == 'weekly' else 5000.00

            subscription = Subscription(
                user_id=student.id,
                subscription_type=subscription_type,
                start_date=start_date,
                end_date=end_date,
                price=price,
                meals_remaining=meals_count,
                is_active=True
            )

            db.session.add(subscription)

        db.session.commit()

    if Order.query.count() == 0:

        students = User.query.filter_by(role='student').all()
        menu_items = MenuItem.query.all()

        if students and menu_items:
            today = datetime.today().date()

            for i, student in enumerate(students):
                num_orders = 1 if i == 0 else 2

                for j in range(num_orders):
                    menu_item = menu_items[(i + j) % len(menu_items)]
                    meal_time = 'breakfast' if j == 0 else 'lunch'
                    payment_type = 'single' if i == 0 else 'subscription'

                    order = Order(
                        user_id=student.id,
                        menu_item_id=menu_item.id,
                        order_date=today,
                        meal_time=meal_time,
                        quantity=1,
                        status='received' if j == 0 else 'ordered',
                        payment_type=payment_type,
                        payment_status='paid',
                        special_requests='Без лука' if i == 1 else None
                    )

                    db.session.add(order)

            yesterday = today - timedelta(days=1)

            for i, student in enumerate(students):
                menu_item = menu_items[i % len(menu_items)]

                order = Order(
                    user_id=student.id,
                    menu_item_id=menu_item.id,
                    order_date=yesterday,
                    meal_time='lunch',
                    quantity=1,
                    status='received',
                    payment_type='single',
                    payment_status='paid'
                )

                db.session.add(order)

            db.session.commit()

    if Feedback.query.count() == 0:

        orders = Order.query.all()

        if orders:
            for i, order in enumerate(orders[:5]):
                feedback = Feedback(
                    user_id=order.user_id,
                    menu_item_id=order.menu_item_id,
                    rating=5 if i % 2 == 0 else 4,
                    comment='Очень вкусно!' if i % 2 == 0 else 'Неплохо, но могло быть и лучше.'
                )

                db.session.add(feedback)

            db.session.commit()

    if SupplyRequest.query.count() == 0:

        cook = User.query.filter_by(role='cook').first()

        if cook:
            supply_requests = [
                SupplyRequest(
                    cook_id=cook.id,
                    product_name='Картофель',
                    quantity=30,
                    unit='кг',
                    urgency='normal',
                    status='pending',
                    notes='Для приготовления пюре'
                ),
                SupplyRequest(
                    cook_id=cook.id,
                    product_name='Курица',
                    quantity=20,
                    unit='кг',
                    urgency='high',
                    status='approved',
                    notes='Срочно, заканчивается',
                    approved_by=User.query.filter_by(role='admin').first().id,
                    approval_date=datetime.utcnow() - timedelta(days=1)
                ),
                SupplyRequest(
                    cook_id=cook.id,
                    product_name='Молоко',
                    quantity=50,
                    unit='л',
                    urgency='normal',
                    status='rejected',
                    notes='Слишком большой объем',
                    approved_by=User.query.filter_by(role='admin').first().id,
                    approval_date=datetime.utcnow() - timedelta(days=2)
                )
            ]

            for request in supply_requests:
                db.session.add(request)

            db.session.commit()