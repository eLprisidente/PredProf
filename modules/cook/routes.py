from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from modules.core.database import db
from datetime import datetime, date
from sqlalchemy import func
import json
from flask_wtf.csrf import CSRFProtect

cook_bp = Blueprint('cook', __name__)
csrf = CSRFProtect()


@cook_bp.route('/dashboard')
@login_required
def cook_dashboard():
    """Дашборд повара"""
    if current_user.role != 'cook':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import Order, SupplyRequest, Inventory

    # Заказы на сегодня
    today_orders = Order.query.filter(
        Order.order_date == date.today()
    ).order_by(Order.created_at.desc()).all()

    # Статистика
    total_orders = len(today_orders)
    completed_orders = len([o for o in today_orders if o.status == 'received'])

    # Низкий инвентарь
    low_inventory = Inventory.query.filter(
        Inventory.current_quantity <= Inventory.min_quantity
    ).order_by(Inventory.current_quantity).limit(5).all()

    # Ожидающие заявки
    pending_requests = SupplyRequest.query.filter_by(status='pending').count()

    return render_template('cook/dashboard.html',
                           today_orders=today_orders,
                           total_orders=total_orders,
                           completed_orders=completed_orders,
                           pending_requests=pending_requests,
                           low_inventory=low_inventory)


@cook_bp.route('/orders')
@login_required
def manage_orders():
    """Управление заказами на сегодня"""
    if current_user.role != 'cook':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import Order, User
    from datetime import date

    # Получаем заказы на сегодня с информацией о пользователях
    today_orders = Order.query.filter(
        Order.order_date == date.today()
    ).join(User).order_by(
        Order.meal_time,
        Order.created_at
    ).all()

    # Группируем по времени приема пищи
    breakfast_orders = [o for o in today_orders if o.meal_time == 'breakfast']
    lunch_orders = [o for o in today_orders if o.meal_time == 'lunch']

    # Статистика
    total_orders = len(today_orders)
    completed_orders = len([o for o in today_orders if o.status == 'received'])
    pending_orders = len([o for o in today_orders if o.status not in ['received', 'cancelled']])
    cancelled_orders = len([o for o in today_orders if o.status == 'cancelled'])

    return render_template('cook/orders.html',
                           breakfast_orders=breakfast_orders,
                           lunch_orders=lunch_orders,
                           total_orders=total_orders,
                           completed_count=completed_orders,
                           pending_count=pending_orders,
                           cancelled_count=cancelled_orders)


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

    return jsonify({'success': True, 'message': f'Заказ #{order.id} отмечен как выданный'})


@cook_bp.route('/order/<int:order_id>/cancel', methods=['POST'])
@login_required
def cancel_order(order_id):
    if current_user.role != 'cook':
        return jsonify({'success': False, 'message': 'Доступ запрещен'}), 403

    from modules.core.models import Order

    order = Order.query.get_or_404(order_id)

    if order.status == 'received':
        return jsonify({'success': False, 'message': 'Нельзя отменить выданный заказ'}), 400

    order.status = 'cancelled'
    db.session.commit()

    return jsonify({'success': True, 'message': f'Заказ #{order.id} отменен'})


@cook_bp.route('/inventory')
@login_required
def view_inventory():
    """Просмотр инвентаря"""
    if current_user.role != 'cook':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import Inventory

    # Получаем весь инвентарь
    inventory_items = Inventory.query.order_by(
        Inventory.category,
        Inventory.product_name
    ).all()

    # Группируем по категориям
    categories = {}
    for item in inventory_items:
        if item.category not in categories:
            categories[item.category] = []
        categories[item.category].append(item)

    # Статистика
    total_items = len(inventory_items)
    low_stock_items = len([i for i in inventory_items if i.current_quantity <= i.min_quantity])
    out_of_stock_items = len([i for i in inventory_items if i.current_quantity == 0])

    return render_template('cook/inventory.html',
                           categories=categories,
                           total_items=total_items,
                           low_stock_items=low_stock_items,
                           out_of_stock_items=out_of_stock_items)


@cook_bp.route('/inventory/<int:item_id>/update', methods=['GET', 'POST'])
@login_required
def update_inventory(item_id):
    """Обновить количество инвентаря"""
    if current_user.role != 'cook':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import Inventory
    from .forms import InventoryUpdateForm

    item = Inventory.query.get_or_404(item_id)
    form = InventoryUpdateForm(obj=item)

    if form.validate_on_submit():
        item.current_quantity = form.current_quantity.data
        item.min_quantity = form.min_quantity.data
        item.last_updated = datetime.utcnow()

        # Добавляем заметку в историю
        if form.notes.data:
            # Здесь можно добавить логику для истории изменений
            pass

        db.session.commit()

        flash(f'Инвентарь "{item.product_name}" обновлен', 'success')
        return redirect(url_for('cook.view_inventory'))

    return render_template('cook/update_inventory.html', form=form, item=item)


@cook_bp.route('/inventory/new', methods=['GET', 'POST'])
@login_required
def new_inventory_item():
    """Добавить новый продукт в инвентарь"""
    if current_user.role != 'cook':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import Inventory
    from .forms import InventoryItemForm

    form = InventoryItemForm()

    if form.validate_on_submit():
        # Проверяем, нет ли уже такого продукта
        existing = Inventory.query.filter_by(product_name=form.product_name.data).first()
        if existing:
            flash(f'Продукт "{form.product_name.data}" уже есть в инвентаре', 'warning')
            return redirect(url_for('cook.update_inventory', item_id=existing.id))

        inventory_item = Inventory(
            product_name=form.product_name.data,
            current_quantity=form.current_quantity.data,
            min_quantity=form.min_quantity.data,
            unit=form.unit.data,
            category=form.category.data
        )

        db.session.add(inventory_item)
        db.session.commit()

        flash(f'Продукт "{inventory_item.product_name}" добавлен в инвентарь', 'success')
        return redirect(url_for('cook.view_inventory'))

    return render_template('cook/new_inventory_item.html', form=form)


@cook_bp.route('/supply-requests')
@login_required
def supply_requests():
    """Список заявок на закупку"""
    if current_user.role != 'cook':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import SupplyRequest, User

    # Получаем все заявки с информацией о согласовании
    requests = SupplyRequest.query.join(
        User, SupplyRequest.approved_by == User.id, isouter=True
    ).order_by(
        SupplyRequest.urgency.desc(),
        SupplyRequest.created_at.desc()
    ).all()

    # Статистика
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
    """Новая заявка на закупку"""
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
    """Отменить заявку на закупку"""
    if current_user.role != 'cook':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import SupplyRequest

    request = SupplyRequest.query.get_or_404(request_id)

    # Проверяем, что заявка принадлежит текущему повару или пользователь - админ
    if request.cook_id != current_user.id and current_user.role != 'admin':
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
    """Управление меню"""
    if current_user.role != 'cook':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import MenuItem

    # Группируем блюда по категориям
    breakfast_items = MenuItem.query.filter_by(category='breakfast').order_by(MenuItem.name).all()
    lunch_items = MenuItem.query.filter_by(category='lunch').order_by(MenuItem.name).all()
    snack_items = MenuItem.query.filter_by(category='snack').order_by(MenuItem.name).all()

    return render_template('cook/menu_management.html',
                           breakfast_items=breakfast_items,
                           lunch_items=lunch_items,
                           snack_items=snack_items)


@cook_bp.route('/menu/new', methods=['GET', 'POST'])
@login_required
def new_menu_item():
    """Добавить новое блюдо"""
    if current_user.role != 'cook':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import MenuItem
    from .forms import MenuItemForm

    form = MenuItemForm()

    if form.validate_on_submit():
        menu_item = MenuItem(
            name=form.name.data,
            description=form.description.data,
            price=float(form.price.data),
            category=form.category.data,
            meal_type=form.meal_type.data,
            allergens=form.allergens.data,
            available=form.available.data
        )

        db.session.add(menu_item)
        db.session.commit()

        flash(f'Блюдо "{menu_item.name}" успешно добавлено!', 'success')
        return redirect(url_for('cook.manage_menu'))

    return render_template('cook/new_menu_item.html', form=form)


@cook_bp.route('/menu/<int:item_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_menu_item(item_id):
    """Редактировать блюдо"""
    if current_user.role != 'cook':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import MenuItem
    from .forms import MenuItemForm

    menu_item = MenuItem.query.get_or_404(item_id)
    form = MenuItemForm(obj=menu_item)

    if form.validate_on_submit():
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
    """Удалить блюдо"""
    if current_user.role != 'cook':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import MenuItem, Order

    menu_item = MenuItem.query.get_or_404(item_id)

    # Проверяем, есть ли активные заказы с этим блюдом
    active_orders = Order.query.filter_by(
        menu_item_id=item_id,
        status='ordered'
    ).first()

    if active_orders:
        flash('Нельзя удалить блюдо, на которое есть активные заказы', 'danger')
        return redirect(url_for('cook.manage_menu'))

    db.session.delete(menu_item)
    db.session.commit()

    flash(f'Блюдо "{menu_item.name}" удалено', 'success')
    return redirect(url_for('cook.manage_menu'))


@cook_bp.route('/menu/<int:item_id>/toggle', methods=['POST'])
@login_required
def toggle_menu_item(item_id):
    """Включить/выключить доступность блюда"""
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
        'available': menu_item.available
    })


@cook_bp.route('/api/today-orders')
@login_required
def api_today_orders():
    """API для получения заказов на сегодня"""
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
            'menu_item': order.menu_item.name,
            'quantity': order.quantity,
            'meal_time': order.meal_time,
            'status': order.status,
            'created_at': order.created_at.strftime('%H:%M')
        })

    return jsonify({'orders': orders_data})


@cook_bp.route('/api/low-inventory')
@login_required
def api_low_inventory():
    """API для получения инвентаря с низким запасом"""
    if current_user.role != 'cook':
        return jsonify({'error': 'Доступ запрещен'}), 403

    from modules.core.models import Inventory

    low_items = Inventory.query.filter(
        Inventory.current_quantity <= Inventory.min_quantity
    ).order_by(Inventory.current_quantity).all()

    items_data = []
    for item in low_items:
        items_data.append({
            'id': item.id,
            'name': item.product_name,
            'current': item.current_quantity,
            'min': item.min_quantity,
            'unit': item.unit,
            'status': 'danger' if item.current_quantity == 0 else 'warning'
        })

    return jsonify({'items': items_data})
