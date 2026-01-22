from flask import Blueprint, render_template, request, flash, redirect, url_for, session, jsonify
from flask_login import login_required, current_user
from modules.core.database import db
from datetime import datetime, date, timedelta
from werkzeug.utils import secure_filename
import os

user_bp = Blueprint('user', __name__)


def get_cart_count():
    """Получить количество товаров в корзине из сессии"""
    cart = session.get('cart', {})
    total = sum(item.get('quantity', 0) for item in cart.values())
    return total


@user_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'student':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import MenuItem, Order, Subscription

    # Сегодняшние заказы пользователя
    today_orders = Order.query.filter_by(
        user_id=current_user.id,
        order_date=date.today()
    ).order_by(Order.created_at.desc()).all()

    # Все заказы пользователя (для истории)
    all_orders = Order.query.filter_by(
        user_id=current_user.id
    ).order_by(Order.order_date.desc(), Order.created_at.desc()).limit(10).all()

    # Меню на сегодня (показываем все доступные блюда)
    today_menu_items = MenuItem.query.filter_by(
        available=True
    ).order_by(MenuItem.category, MenuItem.name).all()

    # Статистика
    orders_count = Order.query.filter_by(user_id=current_user.id).count()
    today_orders_count = len(today_orders)

    # Баланс и абонементы
    user_balance = 0
    subscription_count = Subscription.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).count()

    return render_template('user/dashboard.html',
                           orders=all_orders,
                           today_orders=today_orders,
                           today_menu_items=today_menu_items,
                           orders_count=orders_count,
                           today_orders_count=today_orders_count,
                           user_balance=user_balance,
                           subscription_count=subscription_count,
                           today_date=date.today().strftime('%d.%m.%Y'))


@user_bp.route('/menu')
@login_required
def show_menu():
    if current_user.role != 'student':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import MenuItem

    breakfast_items = MenuItem.query.filter_by(
        category='breakfast',
        available=True
    ).all()

    lunch_items = MenuItem.query.filter_by(
        category='lunch',
        available=True
    ).all()

    return render_template('user/menu.html',
                           breakfast_items=breakfast_items,
                           lunch_items=lunch_items)


@user_bp.route('/cart')
@login_required
def view_cart():
    """Просмотр корзины"""
    if current_user.role != 'student':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import MenuItem
    from datetime import date, timedelta

    cart = session.get('cart', {})
    cart_items = []
    total_price = 0
    total_items = 0

    for item_id, item_data in cart.items():
        menu_item = MenuItem.query.get(int(item_id))
        if menu_item and menu_item.available:
            quantity = item_data.get('quantity', 1)
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

    # Форматируем даты для Flatpickr
    min_date_flatpickr = min_date.strftime('%Y-%m-%d')
    max_date_flatpickr = max_date.strftime('%Y-%m-%d')
    default_date_flatpickr = today.strftime('%Y-%m-%d')

    # Форматируем даты для отображения
    min_date_display = min_date.strftime('%d.%m.%Y')
    max_date_display = max_date.strftime('%d.%m.%Y')
    default_date_display = today.strftime('%d.%m.%Y')

    return render_template('user/cart.html',
                           cart_items=cart_items,
                           total_price=total_price,
                           total_items=total_items,
                           today=today,
                           min_date=min_date_display,
                           max_date=max_date_display,
                           default_date=default_date_display,
                           min_date_flatpickr=min_date_flatpickr,
                           max_date_flatpickr=max_date_flatpickr,
                           default_date_flatpickr=default_date_flatpickr)


@user_bp.route('/cart/add/<int:item_id>', methods=['POST'])
@login_required
def add_to_cart(item_id):
    """Добавить товар в корзину"""
    if current_user.role != 'student':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import MenuItem

    menu_item = MenuItem.query.get_or_404(item_id)

    if not menu_item.available:
        flash('Товар недоступен', 'warning')
        return redirect(url_for('user.show_menu'))

    cart = session.get('cart', {})

    if str(item_id) in cart:
        cart[str(item_id)]['quantity'] += 1
    else:
        cart[str(item_id)] = {
            'quantity': 1,
            'name': menu_item.name,
            'price': float(menu_item.price),
            'image': menu_item.image_url or None
        }
    flash(f'Товар добавлен в корзину', 'success')

    session['cart'] = cart
    session.modified = True

    # Перенаправляем на ту же страницу, откуда пришел запрос
    return redirect(request.referrer or url_for('user.show_menu'))


@user_bp.route('/cart/update/<int:item_id>', methods=['POST'])
@login_required
def update_cart_item(item_id):
    """Обновить количество товара в корзине"""
    if current_user.role != 'student':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('user.view_cart'))

    action = request.form.get('action')
    cart = session.get('cart', {})

    if str(item_id) in cart:
        if action == 'increase':
            cart[str(item_id)]['quantity'] += 1
            flash(f'Количество увеличено', 'success')
        elif action == 'decrease':
            if cart[str(item_id)]['quantity'] > 1:
                cart[str(item_id)]['quantity'] -= 1
                flash(f'Количество уменьшено', 'success')
            else:
                # Если количество 1 и нажали уменьшить, удаляем товар
                item_name = cart[str(item_id)].get('name', 'Товар')
                del cart[str(item_id)]
                flash(f'{item_name} удален из корзины', 'success')

    session['cart'] = cart
    session.modified = True

    return redirect(url_for('user.view_cart'))


@user_bp.route('/cart/remove/<int:item_id>', methods=['POST'])
@login_required
def remove_from_cart(item_id):
    """Удалить товар из корзины"""
    if current_user.role != 'student':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('user.view_cart'))

    cart = session.get('cart', {})

    if str(item_id) in cart:
        del cart[str(item_id)]
        session['cart'] = cart
        session.modified = True
        flash('Товар удален из корзины', 'success')

    return redirect(url_for('user.view_cart'))


@user_bp.route('/cart/clear', methods=['POST'])
@login_required
def clear_cart():
    """Очистить корзину"""
    if current_user.role != 'student':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    session['cart'] = {}
    session.modified = True
    flash('Корзина очищена', 'info')

    return redirect(url_for('user.view_cart'))


@user_bp.route('/cart/checkout', methods=['POST'])
@login_required
def checkout():
    """Оформить заказ из корзины"""
    if current_user.role != 'student':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import MenuItem, Order, Subscription
    from datetime import datetime, date, timedelta

    cart = session.get('cart', {})

    if not cart:
        flash('Корзина пуста', 'warning')
        return redirect(url_for('user.view_cart'))

    try:
        meal_time = request.form.get('meal_time')
        order_date_str = request.form.get('order_date')  # Формат: YYYY-MM-DD
        special_requests = request.form.get('special_requests', '')
        payment_type = request.form.get('payment_type', 'single')

        if not meal_time or not order_date_str:
            flash('Заполните все обязательные поля', 'danger')
            return redirect(url_for('user.view_cart'))

        # Преобразуем дату из формата YYYY-MM-DD
        try:
            order_date = datetime.strptime(order_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Некорректный формат даты', 'danger')
            return redirect(url_for('user.view_cart'))

        # Проверяем, что дата не в прошлом
        if order_date < date.today():
            flash('Нельзя заказать на прошедшую дату', 'danger')
            return redirect(url_for('user.view_cart'))

        # Проверяем, что дата не слишком далеко в будущем
        max_date = date.today() + timedelta(days=7)
        if order_date > max_date:
            flash('Можно заказать максимум на 7 дней вперед', 'danger')
            return redirect(url_for('user.view_cart'))

        # Проверяем абонемент
        if payment_type == 'subscription':
            active_subscription = Subscription.query.filter_by(
                user_id=current_user.id,
                is_active=True
            ).first()

            if not active_subscription or active_subscription.end_date < date.today():
                flash('У вас нет действующего абонемента. Выберите разовую оплату или приобретите абонемент.', 'danger')
                return redirect(url_for('user.view_cart'))

        # Создаем заказы
        orders_created = []

        for item_id, item_data in cart.items():
            menu_item = MenuItem.query.get(int(item_id))
            if menu_item and menu_item.available:
                order = Order(
                    user_id=current_user.id,
                    menu_item_id=int(item_id),
                    order_date=order_date,
                    meal_time=meal_time,
                    quantity=item_data.get('quantity', 1),
                    payment_type=payment_type,
                    payment_status='pending',
                    special_requests=special_requests
                )
                db.session.add(order)
                orders_created.append(order)

        db.session.commit()

        # Очищаем корзину
        session['cart'] = {}
        session.modified = True

        flash(f'Создано {len(orders_created)} заказов. Теперь их можно оплатить.', 'success')
        return redirect(url_for('user.my_orders'))

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при оформлении заказа: {str(e)}', 'danger')
        return redirect(url_for('user.view_cart'))


@user_bp.route('/order/new', methods=['GET', 'POST'])
@login_required
def create_order():
    if current_user.role != 'student':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import MenuItem
    from .forms import OrderForm

    form = OrderForm()

    form.menu_item_id.choices = [(item.id, f"{item.name} - {item.price} руб.")
                                 for item in MenuItem.query.filter_by(available=True).all()]

    if form.validate_on_submit():
        from modules.core.models import Order
        order = Order(
            user_id=current_user.id,
            menu_item_id=form.menu_item_id.data,
            order_date=form.order_date.data,
            meal_time=form.meal_time.data,
            quantity=form.quantity.data,
            payment_type=form.payment_type.data,
            payment_status='pending',
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
    if current_user.role != 'student':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import Order
    from datetime import datetime

    # Получаем фильтр из запроса
    filter_type = request.args.get('filter', 'all')

    # Базовый запрос
    query = Order.query.filter_by(user_id=current_user.id)

    # Применяем фильтры
    if filter_type == 'pending':
        query = query.filter_by(payment_status='pending')
    elif filter_type == 'paid':
        query = query.filter_by(payment_status='paid')
    elif filter_type == 'received':
        query = query.filter_by(status='received')
    elif filter_type == 'today':
        today = datetime.today().date()
        query = query.filter_by(order_date=today)

    # Сортировка
    user_orders = query.order_by(Order.order_date.desc(), Order.created_at.desc()).all()

    return render_template('user/orders.html', orders=user_orders)


@user_bp.route('/api/check-subscription')
@login_required
def check_subscription():
    """API для проверки наличия действующего абонемента"""
    if current_user.role != 'student':
        return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403

    from modules.core.models import Subscription

    # Ищем активный абонемент
    active_subscription = Subscription.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).first()

    has_subscription = False
    if active_subscription and active_subscription.end_date >= date.today():
        has_subscription = True

    return jsonify({
        'success': True,
        'has_subscription': has_subscription,
        'subscription': {
            'type': active_subscription.subscription_type if active_subscription else None,
            'end_date': active_subscription.end_date.strftime('%d.%m.%Y') if active_subscription else None
        }
    })


@user_bp.route('/order/<int:order_id>/pay', methods=['POST'])
@login_required
def pay_for_order(order_id):
    if current_user.role != 'student':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import Order
    from modules.core.services.payment_service import PaymentService

    order = Order.query.get_or_404(order_id)

    if order.user_id != current_user.id:
        flash('Это не ваш заказ!', 'danger')
        return redirect(url_for('user.my_orders'))

    if order.payment_status == 'paid':
        flash('Заказ уже оплачен', 'info')
        return redirect(url_for('user.my_orders'))

    if order.payment_type == 'single':
        success, message = PaymentService.process_single_payment(order.id)
        if success:
            flash('Заказ успешно оплачен!', 'success')
        else:
            flash(f'Ошибка оплаты: {message}', 'danger')

    elif order.payment_type == 'subscription':
        subscription = PaymentService.check_subscription_status(current_user.id)

        if not subscription:
            flash('У вас нет активного абонемента', 'warning')
            return redirect(url_for('user.purchase_subscription'))

        success, message = PaymentService.use_subscription_for_order(order.id, subscription.id)
        if success:
            flash('Оплачено по абонементу', 'success')
        else:
            flash(f'Ошибка: {message}', 'danger')

    return redirect(url_for('user.my_orders'))


@user_bp.route('/subscription/buy', methods=['GET', 'POST'])
@login_required
def purchase_subscription():
    if current_user.role != 'student':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.services.payment_service import PaymentService

    if request.method == 'POST':
        subscription_type = request.form.get('subscription_type')

        if subscription_type not in ['weekly', 'monthly']:
            flash('Неверный тип абонемента', 'danger')
            return redirect(url_for('user.purchase_subscription'))

        success, result = PaymentService.process_subscription_payment(
            current_user.id,
            subscription_type
        )

        if success:
            flash('Абонемент успешно приобретен!', 'success')
            return redirect(url_for('user.dashboard'))
        else:
            flash(f'Ошибка: {result}', 'danger')

    return render_template('user/buy_subscription.html')


@user_bp.route('/order/<int:order_id>/receive', methods=['POST'])
@login_required
def mark_order_received(order_id):
    if current_user.role != 'student':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import Order

    order = Order.query.get_or_404(order_id)

    if order.user_id != current_user.id:
        flash('Это не ваш заказ!', 'danger')
        return redirect(url_for('user.my_orders'))

    if order.payment_status != 'paid':
        flash('Заказ не оплачен', 'warning')
        return redirect(url_for('user.my_orders'))

    if order.status == 'received':
        flash('Заказ уже получен', 'info')
        return redirect(url_for('user.my_orders'))

    if order.order_date != date.today():
        flash('Можно отмечать только сегодняшние заказы', 'warning')
        return redirect(url_for('user.my_orders'))

    order.status = 'received'
    db.session.commit()

    flash('Заказ отмечен как полученный', 'success')
    return redirect(url_for('user.my_orders'))


@user_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if current_user.role != 'student':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from .forms import ProfileForm
    from modules.core.models import Order

    form = ProfileForm(obj=current_user)

    # Устанавливаем email (только для отображения, не для изменения)
    form.email.data = current_user.email

    # Подсчет заказов пользователя
    orders_count = Order.query.filter_by(user_id=current_user.id).count()

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

    return render_template('user/profile.html',
                           form=form,
                           orders_count=orders_count,
                           current_user=current_user)


def allowed_file(filename):
    """Проверка разрешенных расширений файлов"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS