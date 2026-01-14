from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from modules.core.database import db
from datetime import datetime

user_bp = Blueprint('user', __name__)


@user_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'student':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import MenuItem, Order

    today_orders = Order.query.filter_by(
        user_id=current_user.id,
        order_date=datetime.today().date()
    ).all()

    menu_items = MenuItem.query.filter_by(available=True).all()

    return render_template('user/dashboard.html',
                           orders=today_orders,
                           menu_items=menu_items)


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


@user_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if current_user.role != 'student':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from .forms import ProfileForm

    form = ProfileForm(obj=current_user)

    if form.validate_on_submit():
        current_user.full_name = form.full_name.data
        current_user.class_group = form.class_group.data
        current_user.allergies = form.allergies.data

        db.session.commit()
        flash('Профиль успешно обновлен!', 'success')
        return redirect(url_for('user.profile'))

    return render_template('user/profile.html', form=form)


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

    user_orders = Order.query.filter_by(user_id=current_user.id) \
        .order_by(Order.order_date.desc()) \
        .all()

    return render_template('user/orders.html', orders=user_orders)


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
    from datetime import datetime

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

    if order.order_date != datetime.today().date():
        flash('Можно отмечать только сегодняшние заказы', 'warning')
        return redirect(url_for('user.my_orders'))

    order.status = 'received'
    db.session.commit()

    flash('Заказ отмечен как полученный', 'success')
    return redirect(url_for('user.my_orders'))