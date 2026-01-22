from flask import Blueprint, render_template, request, flash, redirect, url_for, session, jsonify
from modules.core.database import db
from datetime import datetime, date, timedelta
import os
from werkzeug.utils import secure_filename
from flask_login import login_required, current_user


# Функция для проверки разрешенных файлов
def allowed_file(filename):
    """Проверяем, что файл - изображение"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


user_bp = Blueprint('user', __name__)


def get_cart_count():
    """Получить количество товаров в корзине из сессии"""
    cart = session.get('cart', {})
    total = sum(item.get('quantity', 0) for item in cart.values())
    return total


# Добавим контекстный процессор для проверки активного абонемента
@user_bp.app_context_processor
def inject_subscription_status():
    """Добавить информацию об абонементе во все шаблоны"""
    from .services import SubscriptionService

    if current_user.is_authenticated and current_user.role == 'student':
        has_active_subscription = SubscriptionService.get_active_subscription(current_user.id) is not None
        return {'has_active_subscription': has_active_subscription}
    return {'has_active_subscription': False}


@user_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'student':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import MenuItem, Order, Subscription
    from datetime import date, datetime, timedelta

    # Сегодняшняя дата
    today = date.today()

    # Отладочная информация
    print(f"DEBUG: Сегодняшняя дата: {today}")

    # Сегодняшние заказы пользователя (включая те, что в работе)
    today_orders = Order.query.filter(
        Order.user_id == current_user.id,
        Order.order_date == today,
        Order.status != 'cancelled'
    ).order_by(Order.created_at.desc()).all()

    # Отладочная информация
    print(f"DEBUG: Найдено заказов на сегодня: {len(today_orders)}")
    for order in today_orders:
        print(f"  Заказ #{order.id}: дата={order.order_date}, статус={order.status}, оплата={order.payment_status}")

    # Все заказы пользователя (для истории)
    all_orders = Order.query.filter(
        Order.user_id == current_user.id,
        Order.status != 'cancelled'
    ).order_by(Order.order_date.desc(), Order.created_at.desc()).limit(10).all()

    # Меню на сегодня (только доступные и НЕ удаленные блюда)
    today_menu_items = MenuItem.query.filter(
        MenuItem.available == True,
        MenuItem.is_deleted == False
    ).order_by(MenuItem.category, MenuItem.name).all()

    # Статистика
    orders_count = Order.query.filter_by(user_id=current_user.id).count()
    today_orders_count = len(today_orders)

    # Абонементы
    subscription_count = Subscription.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).count()

    # Проверяем, есть ли недавние возвраты (за последние 24 часа)
    one_day_ago = datetime.utcnow() - timedelta(days=1)
    recent_refunds = Order.query.filter(
        Order.user_id == current_user.id,
        Order.refunded == True,
        Order.refund_date >= one_day_ago
    ).all()

    # Отладочная информация о возвратах
    print(f"DEBUG: Найдено возвратов за 24 часа: {len(recent_refunds)}")

    return render_template('user/dashboard.html',
                           orders=all_orders,
                           today_orders=today_orders,
                           today_menu_items=today_menu_items,
                           orders_count=orders_count,
                           today_orders_count=today_orders_count,
                           subscription_count=subscription_count,
                           recent_refunds=recent_refunds,
                           today_date=today.strftime('%d.%m.%Y'),
                           today=today)


# Добавляем функцию пополнения баланса
@user_bp.route('/profile/balance/add', methods=['POST'])
@login_required
def add_balance():
    if current_user.role != 'student':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('user.profile'))

    from modules.core.models import User
    from .forms import BalanceForm

    form = BalanceForm()

    if form.validate_on_submit():
        amount = float(form.amount.data)

        # Проверяем минимальную сумму
        if amount < 10:
            flash('Минимальная сумма пополнения - 10 ₽', 'danger')
            return redirect(url_for('user.profile'))

        # Проверяем максимальную сумму
        if amount > 10000:
            flash('Максимальная сумма пополнения - 10 000 ₽', 'danger')
            return redirect(url_for('user.profile'))

        # Пополняем баланс
        current_user.balance += amount

        # Создаем транзакцию
        from modules.core.models import Transaction
        transaction = Transaction(
            user_id=current_user.id,
            amount=amount,
            transaction_type='deposit',
            status='completed',
            description=f'Пополнение баланса на {amount} ₽'
        )
        db.session.add(transaction)

        db.session.commit()

        flash(f'Баланс успешно пополнен на {amount} ₽. Текущий баланс: {current_user.balance} ₽', 'success')
        return redirect(url_for('user.profile'))

    # Если форма не валидна, показываем ошибки
    for field, errors in form.errors.items():
        for error in errors:
            flash(f'Ошибка: {error}', 'danger')

    return redirect(url_for('user.profile'))


@user_bp.route('/menu')
@login_required
def show_menu():
    if current_user.role != 'student':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import MenuItem

    # Получаем только доступные и НЕ удаленные блюда
    breakfast_items = MenuItem.query.filter(
        MenuItem.category == 'breakfast',
        MenuItem.available == True,
        MenuItem.is_deleted == False
    ).all()

    lunch_items = MenuItem.query.filter(
        MenuItem.category == 'lunch',
        MenuItem.available == True,
        MenuItem.is_deleted == False
    ).all()

    return render_template('user/menu.html',
                           breakfast_items=breakfast_items,
                           lunch_items=lunch_items)


# modules/user/routes.py (обновленная функция view_cart)
@user_bp.route('/cart')
@login_required
def view_cart():
    """Просмотр корзины"""
    if current_user.role != 'student':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import MenuItem
    from datetime import date, timedelta
    from .services import SubscriptionService
    from .forms import OrderForm  # Добавляем импорт формы

    cart = session.get('cart', {})
    cart_items = []
    total_price = 0
    total_items = 0

    for item_id, item_data in cart.items():
        if isinstance(item_data, dict):
            quantity = item_data.get('quantity', 1)
        else:
            quantity = item_data
            session['cart'][str(item_id)] = {'quantity': quantity}

        menu_item = MenuItem.query.get(int(item_id))
        if menu_item and menu_item.available and not menu_item.is_deleted:
            item_total = menu_item.price * quantity
            cart_items.append({
                'id': item_id,
                'menu_item': menu_item,
                'quantity': quantity,
                'item_total': item_total
            })
            total_price += item_total
            total_items += quantity

    # Определяем доступные даты
    today = date.today()
    min_date = today
    max_date = today + timedelta(days=7)

    # Проверяем наличие активного абонемента
    active_subscription = SubscriptionService.get_active_subscription(current_user.id)

    # Получаем доступные способы оплаты
    from .services import PaymentService
    payment_options = PaymentService.get_payment_options(current_user.id)

    # Создаем форму для CSRF защиты
    form = OrderForm()

    # Сохраняем обновленную корзину
    session.modified = True

    return render_template('user/cart.html',
                           cart_items=cart_items,
                           total_price=total_price,
                           total_items=total_items,
                           today=today,
                           min_date=min_date,  # Передаем объект date
                           max_date=max_date,  # Передаем объект date
                           default_date=today.strftime('%Y-%m-%d'),  # Для value input
                           active_subscription=active_subscription,
                           payment_options=payment_options,
                           form=form)  # Добавляем форму


@user_bp.route('/cart/add/<int:item_id>', methods=['POST'])
@login_required
def add_to_cart(item_id):
    """Добавить блюдо в корзину"""
    if current_user.role != 'student':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import MenuItem

    menu_item = MenuItem.query.get_or_404(item_id)

    if not menu_item.available or menu_item.is_deleted:
        flash('Это блюдо временно недоступно', 'danger')
        return redirect(url_for('user.show_menu'))

    # Получаем количество из формы
    quantity = int(request.form.get('quantity', 1))

    # Инициализируем корзину
    if 'cart' not in session:
        session['cart'] = {}

    # Добавляем товар в корзину (без даты)
    if str(item_id) in session['cart']:
        # Если товар уже в корзине, увеличиваем количество
        current_item = session['cart'][str(item_id)]
        if isinstance(current_item, dict):
            current_item['quantity'] += quantity
        else:
            # Конвертируем старую структуру в новую
            session['cart'][str(item_id)] = {'quantity': current_item + quantity}
    else:
        # Добавляем новый товар
        session['cart'][str(item_id)] = {'quantity': quantity}

    session.modified = True
    flash(f'"{menu_item.name}" добавлен в корзину!', 'success')
    return redirect(request.referrer or url_for('user.show_menu'))


@user_bp.route('/cart/remove/<int:item_id>', methods=['POST'])
@login_required
def remove_from_cart(item_id):
    """Удалить блюдо из корзины"""
    if current_user.role != 'student':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    cart = session.get('cart', {})
    item_id_str = str(item_id)

    if item_id_str in cart:
        del cart[item_id_str]
        session['cart'] = cart
        session.modified = True
        flash('Блюдо удалено из корзины', 'success')

    return redirect(url_for('user.view_cart'))


@user_bp.route('/cart/update/<int:item_id>', methods=['POST'])
@login_required
def update_cart(item_id):
    """Обновить количество блюда в корзине"""
    if current_user.role != 'student':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import MenuItem
    from datetime import date

    quantity = int(request.form.get('quantity', 1))

    if quantity <= 0:
        # Если количество 0 или отрицательное, удаляем товар
        cart = session.get('cart', {})
        item_id_str = str(item_id)

        if item_id_str in cart:
            del cart[item_id_str]
            session['cart'] = cart
            session.modified = True

        flash('Блюдо удалено из корзины', 'success')
        return redirect(url_for('user.view_cart'))

    cart = session.get('cart', {})
    item_id_str = str(item_id)

    if item_id_str in cart:
        item_data = cart[item_id_str]
        if isinstance(item_data, dict):
            item_data['quantity'] = quantity
        else:
            # Конвертируем старую структуру
            cart[item_id_str] = {
                'quantity': quantity,
                'order_date': date.today().isoformat()
            }

        session['cart'] = cart
        session.modified = True

    return redirect(url_for('user.view_cart'))


@user_bp.route('/cart/checkout', methods=['POST'])
@login_required
def checkout():
    """Оформление заказа с выбором способа оплаты"""
    if current_user.role != 'student':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import MenuItem, Order, Transaction
    from datetime import datetime, date
    from .services import SubscriptionService, PaymentService

    # Получаем данные из корзины (сессии)
    cart = session.get('cart', {})

    if not cart:
        flash('Корзина пуста', 'warning')
        return redirect(url_for('user.view_cart'))

    # Получаем выбранную дату заказа
    order_date_str = request.form.get('order_date', date.today().isoformat())
    payment_method = request.form.get('payment_method', 'balance')

    try:
        # Преобразуем строку даты в объект date
        order_date = datetime.strptime(order_date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        order_date = date.today()

    # Проверяем доступность всех блюд в корзине и рассчитываем сумму
    total_amount = 0
    cart_items_info = []

    for item_id, item_data in cart.items():
        menu_item = MenuItem.query.get(item_id)
        if not menu_item:
            flash(f'Блюдо с ID {item_id} не найдено', 'danger')
            session.pop('cart', None)
            return redirect(url_for('user.view_cart'))

        if not menu_item.available or menu_item.is_deleted:
            flash(f'Блюдо "{menu_item.name}" больше недоступно', 'danger')
            session.pop('cart', None)
            return redirect(url_for('user.view_cart'))

        # Извлекаем количество из словаря
        quantity = item_data.get('quantity', 1)
        item_total = menu_item.price * quantity
        total_amount += item_total

        cart_items_info.append({
            'menu_item': menu_item,
            'quantity': quantity,
            'item_total': item_total
        })

    # Обработка в зависимости от способа оплаты
    try:
        if payment_method == 'balance':
            # Проверяем достаточность средств
            if current_user.balance < total_amount:
                shortage = total_amount - current_user.balance
                flash(
                    f'Недостаточно средств на балансе. Нужно {total_amount} ₽, на балансе {current_user.balance} ₽. Не хватает {shortage} ₽',
                    'danger')
                return redirect(url_for('user.view_cart'))

            # Списание средств с баланса
            current_user.balance -= total_amount

            # Создаем транзакцию
            transaction = Transaction(
                user_id=current_user.id,
                amount=total_amount,
                transaction_type='payment',
                status='completed',
                description=f'Оплата заказа из корзины'
            )
            db.session.add(transaction)

            payment_status = 'paid'
            payment_type = 'balance'

        elif payment_method == 'subscription':
            # Проверяем наличие активного абонемента
            active_subscription = SubscriptionService.get_active_subscription(current_user.id)
            if not active_subscription:
                flash('У вас нет активного абонемента', 'danger')
                return redirect(url_for('user.view_cart'))

            # Проверяем, достаточно ли приемов пищи в абонементе
            total_quantity = sum(item['quantity'] for item in cart_items_info)
            if active_subscription.meals_remaining < total_quantity:
                flash(
                    f'Недостаточно приемов пищи в абонементе. Осталось: {active_subscription.meals_remaining}, нужно: {total_quantity}',
                    'danger')
                return redirect(url_for('user.view_cart'))

            # Используем абонемент
            active_subscription.meals_remaining -= total_quantity
            if active_subscription.meals_remaining <= 0:
                active_subscription.is_active = False

            payment_status = 'paid'
            payment_type = 'subscription'

        else:
            flash('Неверный способ оплаты', 'danger')
            return redirect(url_for('user.view_cart'))

        # Создаем заказы для каждого блюда в корзине
        for item_info in cart_items_info:
            order = Order(
                user_id=current_user.id,
                menu_item_id=item_info['menu_item'].id,
                order_date=order_date,
                meal_time=request.form.get('meal_time', 'lunch'),
                quantity=item_info['quantity'],
                status='pending',
                payment_type=payment_type,
                payment_status=payment_status,
                subscription_id=active_subscription.id if payment_method == 'subscription' else None,
                special_requests=request.form.get('special_requests', '')
            )
            db.session.add(order)

        db.session.commit()

        # Очищаем корзину
        session.pop('cart', None)

        flash(f'Заказ успешно оформлен на {order_date.strftime("%d.%m.%Y")}! Способ оплаты: {payment_method}',
              'success')
        return redirect(url_for('user.my_orders'))

    except Exception as e:
        db.session.rollback()
        print(f"Ошибка при оформлении заказа: {e}")
        flash('Ошибка при оформлении заказа', 'danger')
        return redirect(url_for('user.view_cart'))


@user_bp.route('/order/new', methods=['GET', 'POST'])
@login_required
def create_order():
    if current_user.role != 'student':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import MenuItem
    from .forms import OrderForm
    from .services import SubscriptionService, PaymentService

    form = OrderForm()

    # Получаем доступные способы оплаты
    payment_options = PaymentService.get_payment_options(current_user.id)

    # Если есть активный абонемент, добавляем его в выбор оплаты
    if 'subscription' in payment_options:
        form.payment_type.choices = [
            ('single', 'Разовая оплата (с баланса)'),
            ('subscription', 'Оплата абонементом')
        ]
    else:
        form.payment_type.choices = [
            ('single', 'Разовая оплата (с баланса)')
        ]

    form.menu_item_id.choices = [(item.id, f"{item.name} - {item.price} руб.")
                                 for item in MenuItem.query.filter_by(available=True).all()]

    if form.validate_on_submit():
        from modules.core.models import Order, Transaction
        from .services import SubscriptionService

        menu_item = MenuItem.query.get(form.menu_item_id.data)
        total_price = menu_item.price * form.quantity.data

        # Обработка оплаты
        if form.payment_type.data == 'single':
            # Проверяем баланс
            if current_user.balance < total_price:
                flash(f'Недостаточно средств на балансе. Нужно {total_price} ₽', 'danger')
                return redirect(url_for('user.create_order'))

            # Списание с баланса
            current_user.balance -= total_price

            # Создаем транзакцию
            transaction = Transaction(
                user_id=current_user.id,
                amount=total_price,
                transaction_type='payment',
                status='completed',
                description=f'Оплата заказа блюда {menu_item.name}'
            )
            db.session.add(transaction)

            payment_status = 'paid'

        elif form.payment_type.data == 'subscription':
            # Используем абонемент
            active_subscription = SubscriptionService.get_active_subscription(current_user.id)
            if not active_subscription:
                flash('У вас нет активного абонемента', 'danger')
                return redirect(url_for('user.create_order'))

            if active_subscription.meals_remaining < form.quantity.data:
                flash(f'Недостаточно приемов пищи в абонементе. Осталось: {active_subscription.meals_remaining}',
                      'danger')
                return redirect(url_for('user.create_order'))

            # Используем абонемент
            active_subscription.meals_remaining -= form.quantity.data
            if active_subscription.meals_remaining <= 0:
                active_subscription.is_active = False

            payment_status = 'paid'

        else:
            flash('Неверный способ оплаты', 'danger')
            return redirect(url_for('user.create_order'))

        order = Order(
            user_id=current_user.id,
            menu_item_id=form.menu_item_id.data,
            order_date=form.order_date.data,
            meal_time=form.meal_time.data,
            quantity=form.quantity.data,
            payment_type=form.payment_type.data,
            payment_status=payment_status,
            subscription_id=active_subscription.id if form.payment_type.data == 'subscription' else None,
            special_requests=form.special_requests.data
        )

        db.session.add(order)
        db.session.commit()

        flash('Заказ успешно создан!', 'success')
        return redirect(url_for('user.dashboard'))

    return render_template('user/order.html', form=form)


@user_bp.route('/feedback/<int:order_id>', methods=['GET', 'POST'])
@login_required
def leave_feedback(order_id):
    if current_user.role != 'student':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import Order, Feedback
    from .forms import FeedbackForm

    order = Order.query.get_or_404(order_id)

    if order.user_id != current_user.id:
        flash('Это не ваш заказ!', 'danger')
        return redirect(url_for('user.dashboard'))

    form = FeedbackForm()

    if form.validate_on_submit():
        feedback = Feedback(
            user_id=current_user.id,
            menu_item_id=order.menu_item_id,
            rating=form.rating.data,
            comment=form.comment.data
        )

        db.session.add(feedback)
        db.session.commit()

        flash('Спасибо за ваш отзыв!', 'success')
        return redirect(url_for('user.dashboard'))

    return render_template('user/feedback.html', form=form, order=order)


@user_bp.route('/orders')
@login_required
def my_orders():
    """Мои заказы - скрываем заказы с удаленными блюдами"""
    if current_user.role != 'student':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import Order, MenuItem
    from datetime import date, timedelta
    from sqlalchemy import or_

    # Получаем фильтр из параметров запроса
    filter_type = request.args.get('filter', 'all')
    today = date.today()

    # Базовый запрос: заказы пользователя, где блюдо НЕ удалено
    query = Order.query.join(MenuItem).filter(
        Order.user_id == current_user.id,
        MenuItem.is_deleted == False  # Только блюда, которые НЕ удалены
    )

    # Применяем фильтры
    if filter_type == 'today':
        query = query.filter(Order.order_date == today)
    elif filter_type == 'pending':
        query = query.filter(Order.payment_status == 'pending')
    elif filter_type == 'paid':
        query = query.filter(Order.payment_status == 'paid')
    elif filter_type == 'received':
        query = query.filter(Order.status == 'received')
    elif filter_type == 'future':
        query = query.filter(Order.order_date > today)
    elif filter_type == 'cancelled':
        query = query.filter(Order.status == 'cancelled')
    elif filter_type == 'refunded':
        query = query.filter(Order.refunded == True)

    # Сортируем по дате (сначала новые)
    orders = query.order_by(
        Order.order_date.desc(),
        Order.created_at.desc()
    ).all()

    return render_template('user/orders.html',
                           orders=orders,
                           filter_type=filter_type,
                           today=today)


@user_bp.route('/order/<int:order_id>/cancel', methods=['POST'])
@login_required
def cancel_order(order_id):
    """Отменить заказ"""
    if current_user.role != 'student':
        return jsonify({'success': False, 'message': 'Доступ запрещен'}), 403

    from modules.core.models import Order
    from datetime import date

    order = Order.query.get_or_404(order_id)

    # Проверяем, что заказ принадлежит пользователю
    if order.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Это не ваш заказ'}), 403

    # Проверяем, что заказ можно отменить
    if order.status == 'received':
        return jsonify({'success': False, 'message': 'Нельзя отменить полученный заказ'}), 400

    # Если заказ оплачен, возвращаем средства
    if order.payment_status == 'paid':
        refund_amount = order.total_price
        current_user.balance += refund_amount

        # Добавляем историю возврата
        from modules.core.models import Transaction
        from datetime import datetime

        transaction = Transaction(
            user_id=current_user.id,
            order_id=order.id,
            amount=refund_amount,
            transaction_type='refund',
            status='completed',
            description=f'Возврат средств за отмену заказа #{order.id}'
        )
        db.session.add(transaction)
        order.refunded = True
        order.refund_amount = refund_amount
        order.refund_date = datetime.utcnow()

    order.status = 'cancelled'
    order.payment_status = 'cancelled' if order.payment_status != 'paid' else 'refunded'
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'Заказ #{order.id} отменен' +
                   (' (средства возвращены на баланс)' if order.payment_status == 'refunded' else '')
    })


@user_bp.route('/api/check-subscription')
@login_required
def check_subscription():
    """API для проверки наличия действующего абонемента"""
    if current_user.role != 'student':
        return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403

    from .services import SubscriptionService

    active_subscription = SubscriptionService.get_active_subscription(current_user.id)

    has_subscription = active_subscription is not None

    return jsonify({
        'success': True,
        'has_subscription': has_subscription,
        'subscription': {
            'id': active_subscription.id if active_subscription else None,
            'type': active_subscription.subscription_type if active_subscription else None,
            'end_date': active_subscription.end_date.strftime('%d.%m.%Y') if active_subscription else None,
            'meals_remaining': active_subscription.meals_remaining if active_subscription else None
        }
    })


@user_bp.route('/order/<int:order_id>/pay', methods=['POST'])
@login_required
def pay_for_order(order_id):
    """Оплатить заказ с баланса"""
    if current_user.role != 'student':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('user.my_orders'))

    from modules.core.models import Order

    order = Order.query.get_or_404(order_id)

    # Проверяем, что заказ принадлежит пользователю
    if order.user_id != current_user.id:
        flash('Это не ваш заказ', 'danger')
        return redirect(url_for('user.my_orders'))

    # Проверяем, что заказ не оплачен
    if order.payment_status == 'paid':
        flash('Этот заказ уже оплачен', 'warning')
        return redirect(url_for('user.my_orders'))

    # Проверяем, что заказ не отменен
    if order.status == 'cancelled':
        flash('Нельзя оплатить отмененный заказ', 'danger')
        return redirect(url_for('user.my_orders'))

    # Вычисляем сумму заказа
    total_price = order.total_price

    # Проверяем достаточно ли средств на балансе
    if current_user.balance < total_price:
        flash(f'Недостаточно средств на балансе. Нужно {total_price} ₽, на балансе {current_user.balance} ₽', 'danger')
        return redirect(url_for('user.my_orders'))

    try:
        # Списание средств с баланса
        current_user.balance -= total_price
        order.payment_status = 'paid'

        # Добавляем историю транзакции
        from datetime import datetime
        from modules.core.models import Transaction

        transaction = Transaction(
            user_id=current_user.id,
            order_id=order.id,
            amount=total_price,
            transaction_type='payment',
            status='completed',
            description=f'Оплата заказа #{order.id}'
        )
        db.session.add(transaction)

        db.session.commit()

        flash(f'Заказ #{order.id} успешно оплачен! Списано {total_price} ₽', 'success')

    except Exception as e:
        db.session.rollback()
        print(f"Ошибка при оплате заказа: {e}")
        flash('Ошибка при оплате заказа', 'danger')

    return redirect(url_for('user.my_orders'))


@user_bp.route('/subscriptions')
@login_required
def my_subscriptions():
    """Мои абонементы"""
    if current_user.role != 'student':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from .services import SubscriptionService

    subscriptions = SubscriptionService.get_user_subscriptions(current_user.id)
    active_subscription = SubscriptionService.get_active_subscription(current_user.id)

    return render_template('user/my_subscriptions.html',
                           subscriptions=subscriptions,
                           active_subscription=active_subscription)


@user_bp.route('/subscription/buy', methods=['GET', 'POST'])
@login_required
def purchase_subscription():
    """Покупка абонемента"""
    if current_user.role != 'student':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from .services import SubscriptionService

    if request.method == 'POST':
        subscription_type = request.form.get('subscription_type')

        if subscription_type not in ['weekly', 'monthly']:
            flash('Неверный тип абонемента', 'danger')
            return redirect(url_for('user.purchase_subscription'))

        success, result = SubscriptionService.purchase_subscription(current_user, subscription_type)

        if success:
            flash('Абонемент успешно приобретен!', 'success')
            return redirect(url_for('user.my_subscriptions'))
        else:
            flash(f'Ошибка: {result}', 'danger')

    return render_template('user/buy_subscription.html')


@user_bp.route('/subscription/<int:subscription_id>/cancel', methods=['POST'])
@login_required
def cancel_subscription(subscription_id):
    """Отмена абонемента"""
    if current_user.role != 'student':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from .services import SubscriptionService

    success, message = SubscriptionService.cancel_subscription(subscription_id)

    if success:
        flash(message, 'success')
    else:
        flash(f'Ошибка: {message}', 'danger')

    return redirect(url_for('user.my_subscriptions'))


@user_bp.route('/order/<int:order_id>/receive', methods=['POST'])
@login_required
def mark_order_received(order_id):
    """Отметить заказ как полученный"""
    if current_user.role != 'student':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('user.my_orders'))

    from modules.core.models import Order
    from datetime import date

    order = Order.query.get_or_404(order_id)

    # Проверяем, что заказ принадлежит пользователю
    if order.user_id != current_user.id:
        flash('Это не ваш заказ', 'danger')
        return redirect(url_for('user.my_orders'))

    # Проверяем, что заказ оплачен
    if order.payment_status != 'paid':
        flash('Сначала нужно оплатить заказ', 'danger')
        return redirect(url_for('user.my_orders'))

    # Проверяем, что заказ на сегодня
    if order.order_date != date.today():
        flash('Заказ можно получить только в день его оформления', 'warning')
        return redirect(url_for('user.my_orders'))

    # Отмечаем заказ как полученный
    order.status = 'received'
    db.session.commit()

    flash(f'Заказ #{order.id} отмечен как полученный!', 'success')
    return redirect(url_for('user.my_orders'))


@user_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if current_user.role != 'student':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from .forms import ProfileForm, BalanceForm
    from modules.core.models import Order
    from .services import SubscriptionService

    form = ProfileForm(obj=current_user)
    balance_form = BalanceForm()

    # Устанавливаем email (только для отображения, не для изменения)
    form.email.data = current_user.email

    # Подсчет заказов пользователя
    orders_count = Order.query.filter_by(user_id=current_user.id).count()

    # Получаем активный абонемент
    active_subscription = SubscriptionService.get_active_subscription(current_user.id)

    # Проверяем, какая форма была отправлена
    if request.method == 'POST':
        if 'submit' in request.form:  # Отправлена форма профиля
            if form.validate_on_submit():
                current_user.full_name = form.full_name.data
                current_user.class_group = form.class_group.data
                current_user.allergies = form.allergies.data

                # Добавляем preferences только если поле есть в форме
                if hasattr(form, 'preferences'):
                    current_user.preferences = form.preferences.data

                # Обработка загрузки аватара (если поле есть в форме)
                if hasattr(form, 'avatar') and form.avatar.data and form.avatar.data.filename:
                    avatar_file = form.avatar.data
                    if allowed_file(avatar_file.filename):
                        # Создаем уникальное имя файла
                        filename = secure_filename(
                            f"user_{current_user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{avatar_file.filename}")

                        # Создаем папку для аватаров, если ее нет
                        avatar_folder = 'static/uploads/avatars'
                        os.makedirs(avatar_folder, exist_ok=True)

                        # Удаляем старый аватар если есть
                        if current_user.avatar_url:
                            old_path = os.path.join(avatar_folder, current_user.avatar_url)
                            if os.path.exists(old_path):
                                os.remove(old_path)

                        # Сохраняем новый аватар
                        avatar_path = os.path.join(avatar_folder, filename)
                        avatar_file.save(avatar_path)
                        current_user.avatar_url = filename

                db.session.commit()
                flash('Профиль успешно обновлен!', 'success')
                return redirect(url_for('user.profile'))

    # Рендерим шаблон с обеими формами
    return render_template('user/profile.html',
                           form=form,
                           balance_form=balance_form,
                           orders_count=orders_count,
                           active_subscription=active_subscription,
                           current_user=current_user)


def allowed_file(filename):
    """Проверка разрешенных расширений файлов"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
