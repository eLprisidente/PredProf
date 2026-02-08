from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app
from flask_login import login_required, current_user
from modules.core.database import db
from datetime import datetime, date, timedelta
from sqlalchemy import func
import json
import os
from werkzeug.utils import secure_filename

cook_bp = Blueprint('cook', __name__)


def allowed_image(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_menu_image(image_file):
    if not image_file or image_file.filename == '':
        return None

    # Проверяем расширение файла
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    if '.' not in image_file.filename:
        return None

    file_ext = image_file.filename.rsplit('.', 1)[1].lower()

    if file_ext not in ALLOWED_EXTENSIONS:
        return None

    filename = secure_filename(image_file.filename)
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    unique_filename = f"menu_{timestamp}_{filename}"

    menu_items_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'menu_items')

    os.makedirs(menu_items_folder, exist_ok=True)

    filepath = os.path.join(menu_items_folder, unique_filename)

    try:
        image_file.save(filepath)

        if os.path.exists(filepath):
            return unique_filename
        else:
            return None
    except Exception as e:
        print(f"Ошибка при сохранении изображения: {e}")
        return None


def cleanup_unused_images():
    from modules.core.models import MenuItem

    used_images = set()
    menu_items = MenuItem.query.filter(MenuItem.image_url.isnot(None)).all()
    for item in menu_items:
        if item.image_url:
            used_images.add(item.image_url)

    menu_items_folder = os.path.join('static', 'uploads', 'menu_items')

    if not os.path.exists(menu_items_folder):
        return

    all_files = os.listdir(menu_items_folder)

    for filename in all_files:
        if filename not in used_images and filename != '.gitkeep':
            try:
                filepath = os.path.join(menu_items_folder, filename)
                os.remove(filepath)
                print(f"Удален неиспользуемый файл: {filename}")
            except Exception as e:
                print(f"Ошибка при удалении файла {filename}: {e}")


@cook_bp.route('/dashboard')
@login_required
def cook_dashboard():
    if current_user.role != 'cook':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import Order, SupplyRequest

    today_orders = Order.query.filter(
        Order.order_date == date.today()
    ).order_by(Order.created_at.desc()).all()

    total_orders = len(today_orders)
    completed_orders = len([o for o in today_orders if o.status == 'received'])

    try:
        pending_requests = SupplyRequest.query.filter_by(status='pending').count()
    except Exception as e:
        print(f"Ошибка при получении заявок: {e}")
        pending_requests = 0  # Временное значение

    return render_template('cook/dashboard.html',
                           today_orders=today_orders,
                           total_orders=total_orders,
                           completed_orders=completed_orders,
                           pending_requests=pending_requests)


@cook_bp.route('/orders')
@login_required
def manage_orders():
    if current_user.role != 'cook':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import Order, User
    from datetime import date

    today_orders = Order.query.filter(
        Order.order_date == date.today()
    ).join(User).order_by(
        Order.meal_time,
        Order.created_at
    ).all()

    breakfast_orders = [o for o in today_orders if o.meal_time == 'breakfast']
    lunch_orders = [o for o in today_orders if o.meal_time == 'lunch']

    total_orders = len(today_orders)
    completed_orders = len([o for o in today_orders if o.status == 'received'])
    ready_orders = len([o for o in today_orders if o.status == 'ready'])
    preparing_orders = len([o for o in today_orders if o.status in ['pending', 'preparing']])
    cancelled_orders = len([o for o in today_orders if o.status == 'cancelled'])

    return render_template('cook/orders.html',
                           breakfast_orders=breakfast_orders,
                           lunch_orders=lunch_orders,
                           total_orders=total_orders,
                           completed_count=completed_orders,
                           ready_count=ready_orders,
                           preparing_count=preparing_orders,
                           cancelled_count=cancelled_orders)


@cook_bp.route('/order/<int:order_id>/mark-ready', methods=['POST'])
@login_required
def mark_order_ready(order_id):
    if current_user.role != 'cook':
        return jsonify({'success': False, 'message': 'Доступ запрещен'}), 403

    from modules.core.models import Order

    order = Order.query.get_or_404(order_id)

    if order.status == 'received':
        return jsonify({'success': False, 'message': 'Заказ уже выдан'}), 400

    if order.status == 'ready':
        return jsonify({'success': False, 'message': 'Заказ уже готов'}), 400

    order.status = 'ready'
    db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'message': f'Заказ #{order.id} помечен как готовый',
            'new_status': 'ready',
            'status_display': order.status_display
        })

    flash(f'Заказ #{order.id} помечен как готовый', 'success')
    return redirect(url_for('cook.manage_orders'))


@cook_bp.route('/order/<int:order_id>/complete', methods=['POST'])
@login_required
def complete_order(order_id):
    if current_user.role != 'cook':
        return jsonify({'success': False, 'message': 'Доступ запрещен'}), 403

    from modules.core.models import Order

    order = Order.query.get_or_404(order_id)

    if order.status == 'received':
        return jsonify({'success': False, 'message': 'Заказ уже выдан'}), 400

    order.status = 'received'
    db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'message': f'Заказ #{order.id} отмечен как выданный',
            'new_status': 'received',
            'status_display': order.status_display
        })

    flash(f'Заказ #{order.id} отмечен как выданный', 'success')
    return redirect(url_for('cook.manage_orders'))


@cook_bp.route('/order/<int:order_id>/cancel', methods=['POST'])
@login_required
def cancel_order(order_id):
    if current_user.role != 'cook':
        return jsonify({'success': False, 'message': 'Доступ запрещен'}), 403

    from modules.core.models import Order, User, Transaction
    from datetime import datetime

    order = Order.query.get_or_404(order_id)

    if order.status == 'received':
        return jsonify({'success': False, 'message': 'Нельзя отменить выданный заказ'}), 400

    was_paid = order.payment_status == 'paid' and not order.refunded
    refund_amount = 0

    if was_paid and order.user:
        refund_amount = order.total_price

        order.user.balance += refund_amount

        order.refunded = True
        order.refund_amount = refund_amount
        order.refund_date = datetime.utcnow()
        order.payment_status = 'refunded'

        transaction = Transaction(
            user_id=order.user_id,
            order_id=order.id,
            amount=refund_amount,
            transaction_type='refund',
            status='completed',
            description=f'Возврат средств за отмененный заказ #{order.id}'
        )
        db.session.add(transaction)

    order.status = 'cancelled'
    db.session.commit()

    message = f'Заказ #{order.id} отменен'
    if was_paid:
        message += f'. Возвращено {refund_amount:.2f} ₽ пользователю {order.user.full_name}'

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'message': message,
            'new_status': 'cancelled',
            'status_display': order.status_display,
            'refunded': was_paid,
            'refund_amount': refund_amount
        })

    flash(message, 'success')
    return redirect(url_for('cook.manage_orders'))


@cook_bp.route('/supply-requests')
@login_required
def supply_requests():
    if current_user.role != 'cook':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import SupplyRequest, User

    try:
        requests = SupplyRequest.query.order_by(
            SupplyRequest.urgency.desc(),
            SupplyRequest.created_at.desc()
        ).all()
    except Exception as e:
        print(f"Ошибка при получении заявок: {e}")
        requests = []

    total_requests = len(requests)
    pending_requests = len([r for r in requests if r.status == 'pending'])
    approved_requests = len([r for r in requests if r.status == 'approved'])

    return render_template('cook/supply_requests.html',
                           requests=requests,
                           total_requests=total_requests,
                           pending_requests=pending_requests,
                           approved_requests=approved_requests)


@cook_bp.route('/supply-request/new', methods=['GET', 'POST'])
@login_required
def new_supply_request():
    if current_user.role != 'cook':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import SupplyRequest
    from .forms import SupplyRequestForm

    form = SupplyRequestForm()

    if form.validate_on_submit():
        supply_request = SupplyRequest(
            cook_id=current_user.id,
            product_name=form.product_name.data,
            quantity=form.quantity.data,
            unit=form.unit.data,
            urgency=form.urgency.data,
            notes=form.notes.data,
            status='pending'
        )

        db.session.add(supply_request)
        db.session.commit()

        flash('Заявка на закупку успешно создана!', 'success')
        return redirect(url_for('cook.supply_requests'))

    return render_template('cook/supply_request_form.html', form=form)


@cook_bp.route('/supply-request/<int:request_id>/cancel', methods=['POST'])
@login_required
def cancel_supply_request(request_id):
    if current_user.role != 'cook':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import SupplyRequest

    request = SupplyRequest.query.get_or_404(request_id)

    if request.cook_id != current_user.id:
        flash('Вы можете отменять только свои заявки', 'danger')
        return redirect(url_for('cook.supply_requests'))

    if request.status != 'pending':
        flash('Можно отменять только ожидающие заявки', 'warning')
        return redirect(url_for('cook.supply_requests'))

    request.status = 'cancelled'
    db.session.commit()

    flash('Заявка отменена', 'success')
    return redirect(url_for('cook.supply_requests'))


@cook_bp.route('/menu')
@login_required
def manage_menu():
    if current_user.role != 'cook':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import MenuItem

    breakfast_items = MenuItem.query.filter(
        MenuItem.category == 'breakfast',
        MenuItem.is_deleted == False
    ).order_by(MenuItem.name).all()

    lunch_items = MenuItem.query.filter(
        MenuItem.category == 'lunch',
        MenuItem.is_deleted == False
    ).order_by(MenuItem.name).all()

    snack_items = MenuItem.query.filter(
        MenuItem.category == 'snack',
        MenuItem.is_deleted == False
    ).order_by(MenuItem.name).all()

    return render_template('cook/menu_management.html',
                           breakfast_items=breakfast_items,
                           lunch_items=lunch_items,
                           snack_items=snack_items)


@cook_bp.route('/menu/new', methods=['GET', 'POST'])
@login_required
def new_menu_item():
    if current_user.role != 'cook':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import MenuItem
    from .forms import MenuItemForm

    form = MenuItemForm()

    if form.validate_on_submit():
        image_filename = None
        if form.image.data:
            image_filename = save_menu_image(form.image.data)
            if not image_filename:
                flash('Ошибка при загрузке изображения. Проверьте формат файла.', 'warning')

        menu_item = MenuItem(
            name=form.name.data,
            description=form.description.data,
            price=float(form.price.data),
            category=form.category.data,
            meal_type=form.meal_type.data,
            allergens=form.allergens.data,
            image_url=image_filename,
            available=form.available.data,
            is_deleted=False
        )

        db.session.add(menu_item)
        db.session.commit()

        flash(f'Блюдо "{menu_item.name}" успешно добавлено!', 'success')
        return redirect(url_for('cook.manage_menu'))

    return render_template('cook/new_menu_item.html', form=form)


@cook_bp.route('/menu/<int:item_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_menu_item(item_id):
    if current_user.role != 'cook':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import MenuItem
    from .forms import MenuItemForm

    menu_item = MenuItem.query.get_or_404(item_id)
    form = MenuItemForm(obj=menu_item)

    if form.validate_on_submit():
        if form.image.data:
            image_filename = save_menu_image(form.image.data)
            if image_filename:
                if menu_item.image_url:
                    try:
                        old_image_path = os.path.join(
                            current_app.config.get('UPLOAD_FOLDER', 'static/uploads'),
                            'menu_items',
                            menu_item.image_url
                        )
                        if os.path.exists(old_image_path):
                            os.remove(old_image_path)
                    except Exception as e:
                        print(f"Ошибка при удалении старого изображения: {e}")

                menu_item.image_url = image_filename

        menu_item.name = form.name.data
        menu_item.description = form.description.data
        menu_item.price = float(form.price.data)
        menu_item.category = form.category.data
        menu_item.meal_type = form.meal_type.data
        menu_item.allergens = form.allergens.data
        menu_item.available = form.available.data

        db.session.commit()

        flash(f'Блюдо "{menu_item.name}" успешно обновлено!', 'success')
        return redirect(url_for('cook.manage_menu'))

    return render_template('cook/edit_menu_item.html', form=form, menu_item=menu_item)


@cook_bp.route('/menu/<int:item_id>/delete', methods=['POST'])
@login_required
def delete_menu_item(item_id):
    if current_user.role != 'cook':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import MenuItem, Order, User, Transaction
    from datetime import datetime

    menu_item = MenuItem.query.get_or_404(item_id)
    item_name = menu_item.name

    thirty_days_ago = datetime.utcnow().date() - timedelta(days=30)

    paid_orders = Order.query.filter(
        Order.menu_item_id == item_id,
        Order.payment_status == 'paid',
        Order.order_date >= thirty_days_ago
    ).all()

    refunded_users = {}
    total_refund = 0

    for order in paid_orders:
        if order.user and not order.refunded:
            refund_amount = order.total_price

            order.user.balance += refund_amount

            order.refunded = True
            order.refund_amount = refund_amount
            order.refund_date = datetime.utcnow()

            transaction = Transaction(
                user_id=order.user_id,
                order_id=order.id,
                amount=refund_amount,
                transaction_type='refund',
                status='completed',
                description=f'Возврат средств за блюдо "{item_name}"'
            )
            db.session.add(transaction)

            if order.user_id not in refunded_users:
                refunded_users[order.user_id] = {
                    'user': order.user,
                    'total_refund': 0,
                    'orders': []
                }

            refunded_users[order.user_id]['total_refund'] += refund_amount
            refunded_users[order.user_id]['orders'].append(order)
            total_refund += refund_amount

    menu_item.is_deleted = True
    menu_item.available = False
    menu_item.name = f"[УДАЛЕНО] {menu_item.name}"

    db.session.commit()

    refund_message = f'Блюдо "{item_name}" удалено'

    if refunded_users:
        user_count = len(refunded_users)
        refund_message += f'. Возвращено {total_refund:.2f} ₽ {user_count} пользователям'

    flash(refund_message, 'success')
    return redirect(url_for('cook.manage_menu'))


@cook_bp.route('/menu/<int:item_id>/toggle', methods=['POST'])
@login_required
def toggle_menu_item(item_id):
    if current_user.role != 'cook':
        return jsonify({'success': False, 'message': 'Доступ запрещен'}), 403

    from modules.core.models import MenuItem

    menu_item = MenuItem.query.get_or_404(item_id)
    menu_item.available = not menu_item.available
    db.session.commit()

    status = 'доступно' if menu_item.available else 'недоступно'
    return jsonify({
        'success': True,
        'message': f'Блюдо теперь {status}',
        'available': menu_item.available,
        'item_id': item_id
    })


@cook_bp.route('/api/today-orders')
@login_required
def api_today_orders():
    if current_user.role != 'cook':
        return jsonify({'error': 'Доступ запрещен'}), 403

    from modules.core.models import Order

    orders = Order.query.filter(
        Order.order_date == date.today(),
        Order.status != 'received'
    ).order_by(Order.created_at).all()

    orders_data = []
    for order in orders:
        orders_data.append({
            'id': order.id,
            'user_name': order.user.full_name,
            'class_group': order.user.class_group,
            'menu_item': order.menu_item.name if order.menu_item else 'Удаленное блюдо',
            'quantity': order.quantity,
            'meal_time': order.meal_time,
            'status': order.status,
            'status_display': order.status_display,
            'created_at': order.created_at.strftime('%H:%M')
        })

    return jsonify({'orders': orders_data})


@cook_bp.route('/api/order-counts')
@login_required
def get_order_counts():
    if current_user.role != 'cook':
        return jsonify({'error': 'Доступ запрещен'}), 403

    from modules.core.models import Order
    from datetime import date

    today_orders = Order.query.filter(
        Order.order_date == date.today(),
        Order.status.in_(['pending', 'preparing', 'ready'])
    ).all()

    pending_preparing = len([o for o in today_orders if o.status in ['pending', 'preparing']])
    ready = len([o for o in today_orders if o.status == 'ready'])
    total = pending_preparing + ready

    return jsonify({
        'success': True,
        'counts': {
            'pending_preparing': pending_preparing,
            'ready': ready,
            'total': total
        },
        'timestamp': datetime.utcnow().isoformat()
    })
