from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from modules.core.database import db
from datetime import datetime, timedelta
from sqlalchemy import func

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import User, Order, SupplyRequest

    total_users = User.query.count()
    total_orders_today = Order.query.filter_by(
        order_date=datetime.today().date()
    ).count()

    total_pending_requests = SupplyRequest.query.filter_by(status='pending').count()

    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()

    return render_template('admin/dashboard.html',
                           total_users=total_users,
                           total_orders_today=total_orders_today,
                           total_pending_requests=total_pending_requests,
                           recent_orders=recent_orders)


@admin_bp.route('/statistics')
@login_required
def view_statistics():
    if current_user.role != 'admin':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import Order, User, MenuItem
    from datetime import datetime, timedelta

    thirty_days_ago = datetime.today().date() - timedelta(days=30)

    total_orders = Order.query.count()
    total_paid_orders = Order.query.filter_by(payment_status='paid').count()

    total_revenue_result = db.session.query(
        db.func.sum(Order.menu_item.price * Order.quantity)
    ).join(MenuItem).filter(Order.payment_status == 'paid').scalar()
    total_revenue = total_revenue_result or 0

    seven_days_ago = datetime.today().date() - timedelta(days=7)

    daily_stats = db.session.query(
        Order.order_date,
        db.func.count(Order.id).label('orders_count'),
        db.func.sum(Order.menu_item.price * Order.quantity).label('daily_revenue')
    ).join(MenuItem).filter(
        Order.order_date >= seven_days_ago,
        Order.payment_status == 'paid'
    ).group_by(
        Order.order_date
    ).order_by(
        Order.order_date
    ).all()

    payment_type_stats = db.session.query(
        Order.payment_type,
        db.func.count(Order.id).label('count')
    ).filter(
        Order.payment_status == 'paid'
    ).group_by(
        Order.payment_type
    ).all()

    popular_dishes = db.session.query(
        Order.menu_item_id,
        db.func.count(Order.id).label('orders_count'),
        db.func.sum(Order.quantity).label('total_quantity')
    ).filter(
        Order.payment_status == 'paid'
    ).group_by(
        Order.menu_item_id
    ).order_by(
        db.func.count(Order.id).desc()
    ).limit(10).all()

    popular_dishes_with_names = []
    for dish in popular_dishes:
        menu_item = MenuItem.query.get(dish.menu_item_id)
        if menu_item:
            popular_dishes_with_names.append({
                'name': menu_item.name,
                'orders_count': dish.orders_count,
                'total_quantity': dish.total_quantity,
                'revenue': menu_item.price * dish.total_quantity
            })

    return render_template('admin/statistics.html',
                           total_orders=total_orders,
                           total_paid_orders=total_paid_orders,
                           total_revenue=total_revenue,
                           daily_stats=daily_stats,
                           payment_type_stats=payment_type_stats,
                           popular_dishes=popular_dishes_with_names)


@admin_bp.route('/supply-requests')
@login_required
def admin_supply_requests():
    if current_user.role != 'admin':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import SupplyRequest

    requests = SupplyRequest.query.order_by(
        SupplyRequest.urgency.desc(),
        SupplyRequest.created_at
    ).all()

    return render_template('admin/supply_requests.html', requests=requests)


@admin_bp.route('/supply-request/<int:request_id>/approve', methods=['GET', 'POST'])
@login_required
def approve_supply_request(request_id):
    if current_user.role != 'admin':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import SupplyRequest
    from .forms import ApprovalForm

    supply_request = SupplyRequest.query.get_or_404(request_id)
    form = ApprovalForm()

    if form.validate_on_submit():
        supply_request.status = form.status.data
        supply_request.approved_by = current_user.id
        supply_request.approval_date = datetime.utcnow()

        if form.notes.data:
            supply_request.notes = (supply_request.notes or '') + f"\n[Админ]: {form.notes.data}"

        db.session.commit()

        status_text = "утверждена" if form.status.data == 'approved' else "отклонена"
        flash(f'Заявка #{supply_request.id} {status_text}', 'success')
        return redirect(url_for('admin.admin_supply_requests'))

    return render_template('admin/approve_request.html', form=form, request=supply_request)


@admin_bp.route('/reports', methods=['GET', 'POST'])
@login_required
def generate_reports():
    if current_user.role != 'admin':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from .forms import ReportForm

    form = ReportForm()

    if form.validate_on_submit():
        flash('Отчет сгенерирован успешно!', 'success')
        return redirect(url_for('admin.generate_reports'))

    return render_template('admin/reports.html', form=form)


@admin_bp.route('/users')
@login_required
def manage_users():
    if current_user.role != 'admin':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import User

    users_list = User.query.order_by(User.role, User.full_name).all()
    return render_template('admin/users.html', users=users_list)


@admin_bp.route('/user/<int:user_id>/manage', methods=['GET', 'POST'])
@login_required
def manage_user(user_id):
    if current_user.role != 'admin':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import User
    from .forms import UserManagementForm

    user = User.query.get_or_404(user_id)
    form = UserManagementForm()

    if form.validate_on_submit():
        if form.action.data == 'deactivate':
            user.is_active = False
            flash(f'Пользователь {user.email} деактивирован', 'success')
        elif form.action.data == 'activate':
            user.is_active = True
            flash(f'Пользователь {user.email} активирован', 'success')
        elif form.action.data == 'change_role' and form.new_role.data:
            user.role = form.new_role.data
            flash(f'Роль пользователя {user.email} изменена на {form.new_role.data}', 'success')

        db.session.commit()
        return redirect(url_for('admin.manage_users'))

    return render_template('admin/manage_user.html', form=form, user=user)


@admin_bp.route('/feedback')
@login_required
def view_feedback():
    if current_user.role != 'admin':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import Feedback

    feedback_list = Feedback.query.order_by(Feedback.created_at.desc()).all()
    return render_template('admin/feedback.html', feedback_list=feedback_list)


@admin_bp.route('/report/generate', methods=['POST'])
@login_required
def generate_report():
    if current_user.role != 'admin':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import Order, User, MenuItem, SupplyRequest
    from datetime import datetime, timedelta

    report_type = request.form.get('report_type', 'daily')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')

    if report_type == 'daily':
        start_date = datetime.today().date()
        end_date = start_date
    elif report_type == 'weekly':
        end_date = datetime.today().date()
        start_date = end_date - timedelta(days=7)
    elif report_type == 'monthly':
        end_date = datetime.today().date()
        start_date = end_date - timedelta(days=30)
    elif report_type == 'custom' and start_date and end_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        flash('Неверные параметры отчета', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    orders = Order.query.filter(
        Order.order_date >= start_date,
        Order.order_date <= end_date
    ).all()

    orders_stats = {
        'total': len(orders),
        'paid': len([o for o in orders if o.payment_status == 'paid']),
        'received': len([o for o in orders if o.status == 'received']),
        'revenue': sum(o.menu_item.price * o.quantity for o in orders if o.payment_status == 'paid')
    }

    users_with_orders = User.query.filter(
        User.orders.any(Order.order_date >= start_date)
    ).all()

    supply_requests = SupplyRequest.query.filter(
        SupplyRequest.created_at >= datetime.combine(start_date, datetime.min.time()),
        SupplyRequest.created_at <= datetime.combine(end_date, datetime.max.time())
    ).all()

    supply_stats = {
        'total': len(supply_requests),
        'approved': len([r for r in supply_requests if r.status == 'approved']),
        'pending': len([r for r in supply_requests if r.status == 'pending']),
        'total_cost': 0
    }

    report = {
        'title': f'Отчет за период с {start_date} по {end_date}',
        'period': {
            'start_date': start_date.strftime('%d.%m.%Y'),
            'end_date': end_date.strftime('%d.%m.%Y'),
            'days': (end_date - start_date).days + 1
        },
        'orders': orders_stats,
        'users': {
            'active': len(users_with_orders),
            'total': User.query.count()
        },
        'supply_requests': supply_stats,
        'generated_at': datetime.now().strftime('%d.%m.%Y %H:%M'),
        'generated_by': current_user.full_name
    }

    return render_template('admin/report_view.html', report=report)