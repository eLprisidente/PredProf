from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from modules.core.database import db
from datetime import datetime

cook_bp = Blueprint('cook', __name__)


@cook_bp.route('/dashboard')
@login_required
def cook_dashboard():
    if current_user.role != 'cook':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import Order, SupplyRequest, Inventory

    today_orders = Order.query.filter_by(
        order_date=datetime.today().date()
    ).all()

    pending_requests = SupplyRequest.query.filter_by(status='pending').count()

    low_inventory = Inventory.query.filter(
        Inventory.current_quantity <= Inventory.min_quantity
    ).all()

    return render_template('cook/dashboard.html',
                           today_orders=today_orders,
                           pending_requests=pending_requests,
                           low_inventory=low_inventory)


@cook_bp.route('/orders')
@login_required
def manage_orders():
    if current_user.role != 'cook':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import Order

    breakfast_orders = Order.query.filter_by(
        order_date=datetime.today().date(),
        meal_time='breakfast'
    ).all()

    lunch_orders = Order.query.filter_by(
        order_date=datetime.today().date(),
        meal_time='lunch'
    ).all()

    return render_template('cook/orders.html',
                           breakfast_orders=breakfast_orders,
                           lunch_orders=lunch_orders)


@cook_bp.route('/order/<int:order_id>/complete', methods=['POST'])
@login_required
def complete_order(order_id):
    if current_user.role != 'cook':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import Order

    order = Order.query.get_or_404(order_id)
    order.status = 'received'
    db.session.commit()

    flash(f'Заказ #{order.id} отмечен как выданный', 'success')
    return redirect(url_for('cook.manage_orders'))


@cook_bp.route('/supply/new', methods=['GET', 'POST'])
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

        flash('Заявка на поставку создана успешно!', 'success')
        return redirect(url_for('cook.supply_requests'))

    return render_template('cook/new_supply.html', form=form)


@cook_bp.route('/supply')
@login_required
def supply_requests():
    if current_user.role != 'cook':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import SupplyRequest

    requests = SupplyRequest.query.order_by(SupplyRequest.created_at.desc()).all()
    return render_template('cook/supply_requests.html', requests=requests)


@cook_bp.route('/inventory')
@login_required
def view_inventory():
    if current_user.role != 'cook':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import Inventory

    inventory_items = Inventory.query.order_by(Inventory.product_name).all()
    return render_template('cook/inventory.html', inventory_items=inventory_items)


@cook_bp.route('/inventory/<int:item_id>/update', methods=['GET', 'POST'])
@login_required
def update_inventory(item_id):
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
        db.session.commit()

        flash(f'Инвентарь {item.product_name} обновлен', 'success')
        return redirect(url_for('cook.view_inventory'))

    return render_template('cook/update_inventory.html', form=form, item=item)


@cook_bp.route('/menu')
@login_required
def manage_menu():
    if current_user.role != 'cook':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import MenuItem

    menu_items = MenuItem.query.order_by(MenuItem.category, MenuItem.name).all()
    return render_template('cook/menu_management.html', menu_items=menu_items)


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

        flash(f'Блюдо "{menu_item.name}" добавлено в меню', 'success')
        return redirect(url_for('cook.manage_menu'))

    return render_template('cook/new_menu_item.html', form=form)


@cook_bp.route('/supply/check-low-stock')
@login_required
def check_low_stock():
    if current_user.role != 'cook':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import Inventory, SupplyRequest

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
            supply_request = SupplyRequest(
                cook_id=current_user.id,
                product_name=item.product_name,
                quantity=int(item.min_quantity * 2),
                unit=item.unit,
                urgency='high' if item.current_quantity == 0 else 'normal',
                notes=f'Автоматическая заявка. Осталось: {item.current_quantity} {item.unit}'
            )

            db.session.add(supply_request)
            created_requests += 1

    if created_requests > 0:
        db.session.commit()
        flash(f'Создано {created_requests} новых заявок на поставку', 'success')
    else:
        flash('Все необходимые заявки уже созданы', 'info')

    return redirect(url_for('cook.supply_requests'))


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
        menu_item.name = form.name.data
        menu_item.description = form.description.data
        menu_item.price = float(form.price.data)
        menu_item.category = form.category.data
        menu_item.meal_type = form.meal_type.data
        menu_item.allergens = form.allergens.data
        menu_item.available = form.available.data

        db.session.commit()

        flash(f'Блюдо "{menu_item.name}" обновлено', 'success')
        return redirect(url_for('cook.manage_menu'))

    return render_template('cook/edit_menu_item.html', form=form, menu_item=menu_item)


@cook_bp.route('/menu/<int:item_id>/delete', methods=['POST'])
@login_required
def delete_menu_item(item_id):
    if current_user.role != 'cook':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import MenuItem

    menu_item = MenuItem.query.get_or_404(item_id)
    db.session.delete(menu_item)
    db.session.commit()

    flash(f'Блюдо "{menu_item.name}" удалено', 'success')
    return redirect(url_for('cook.manage_menu'))


@cook_bp.route('/supply/<int:request_id>/cancel', methods=['POST'])
@login_required
def cancel_supply_request(request_id):
    if current_user.role != 'cook':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import SupplyRequest

    supply_request = SupplyRequest.query.get_or_404(request_id)

    # Проверяем, что заявка принадлежит текущему повару
    if supply_request.cook_id != current_user.id:
        flash('Вы можете отменять только свои заявки', 'danger')
        return redirect(url_for('cook.supply_requests'))

    if supply_request.status != 'pending':
        flash('Можно отменять только ожидающие заявки', 'warning')
        return redirect(url_for('cook.supply_requests'))

    db.session.delete(supply_request)
    db.session.commit()

    flash('Заявка отменена', 'success')
    return redirect(url_for('cook.supply_requests'))