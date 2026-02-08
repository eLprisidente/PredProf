from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, make_response
from flask_login import login_required, current_user
from modules.core.database import db
from datetime import datetime, timedelta
from sqlalchemy import func, or_
import json
import csv
import io

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

    recent_orders = Order.query.options(db.joinedload(Order.menu_item)).order_by(Order.created_at.desc()).limit(
        10).all()

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
        db.func.sum(MenuItem.price * Order.quantity)
    ).select_from(Order).join(
        MenuItem, Order.menu_item_id == MenuItem.id
    ).filter(
        Order.payment_status == 'paid'
    ).scalar()
    total_revenue = total_revenue_result or 0

    seven_days_ago = datetime.today().date() - timedelta(days=7)

    daily_stats = db.session.query(
        Order.order_date,
        db.func.count(Order.id).label('orders_count'),
        db.func.sum(MenuItem.price * Order.quantity).label('daily_revenue')
    ).join(
        MenuItem, Order.menu_item_id == MenuItem.id
    ).filter(
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
        MenuItem,
        db.func.count(Order.id).label('orders_count'),
        db.func.sum(Order.quantity).label('total_quantity')
    ).join(
        Order, MenuItem.id == Order.menu_item_id
    ).filter(
        Order.payment_status == 'paid'
    ).group_by(
        MenuItem.id
    ).order_by(
        db.func.count(Order.id).desc()
    ).limit(10).all()

    popular_dishes_with_names = []
    for dish_data in popular_dishes:
        menu_item, orders_count, total_quantity = dish_data
        if menu_item:
            popular_dishes_with_names.append({
                'name': menu_item.name,
                'orders_count': orders_count,
                'total_quantity': total_quantity,
                'revenue': menu_item.price * total_quantity
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


@admin_bp.route('/feedback')
@login_required
def view_feedback():
    if current_user.role != 'admin':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    from modules.core.models import Feedback

    feedback_list = Feedback.query.order_by(Feedback.created_at.desc()).all()
    return render_template('admin/feedback.html', feedback_list=feedback_list)


@admin_bp.route('/api/user/<int:user_id>')
@login_required
def get_user_api(user_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403

    from modules.core.models import User

    user = User.query.get_or_404(user_id)

    return jsonify({
        'success': True,
        'user': {
            'id': user.id,
            'full_name': user.full_name,
            'email': user.email,
            'role': user.role,
            'class_group': user.class_group,
            'allergies': user.allergies,
            'is_active': user.is_active,
            'created_at': user.created_at.strftime('%Y-%m-%d %H:%M:%S') if user.created_at else None
        }
    })


@admin_bp.route('/api/user/add', methods=['POST'])
@login_required
def api_add_user():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403

    try:
        from modules.core.models import User
        from modules.auth.utils import hash_password

        data = request.json

        required_fields = ['full_name', 'email', 'password', 'role']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'success': False, 'error': f'Отсутствует поле: {field}'}), 400

        if not '@' in data['email']:
            return jsonify({'success': False, 'error': 'Некорректный email'}), 400

        existing_user = User.query.filter_by(email=data['email']).first()
        if existing_user:
            return jsonify({'success': False, 'error': 'Пользователь с таким email уже существует'}), 400

        # Проверяем пароль
        if len(data['password']) < 6:
            return jsonify({'success': False, 'error': 'Пароль должен быть не менее 6 символов'}), 400

        new_user = User(
            email=data['email'],
            password_hash=hash_password(data['password']),
            full_name=data['full_name'],
            role=data['role'],
            is_active=data.get('is_active', True),
            allergies=data.get('allergies', ''),
            class_group=data.get('class_group', '')
        )

        db.session.add(new_user)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Пользователь {new_user.full_name} успешно создан',
            'user_id': new_user.id
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/user/<int:user_id>/update', methods=['POST'])
@login_required
def api_update_user(user_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403

    try:
        from modules.core.models import User
        from modules.auth.utils import hash_password

        user = User.query.get_or_404(user_id)
        data = request.json

        if 'full_name' in data:
            user.full_name = data['full_name']
        if 'email' in data and data['email'] != user.email:
            existing = User.query.filter_by(email=data['email']).first()
            if existing and existing.id != user_id:
                return jsonify({'success': False, 'error': 'Email уже используется другим пользователем'}), 400
            user.email = data['email']
        if 'role' in data:
            user.role = data['role']
        if 'is_active' in data:
            user.is_active = bool(data['is_active'])
        if 'allergies' in data:
            user.allergies = data['allergies']
        if 'class_group' in data:
            user.class_group = data['class_group']

        if 'password' in data and data['password']:
            if len(data['password']) >= 6:
                user.password_hash = hash_password(data['password'])
            else:
                return jsonify({'success': False, 'error': 'Пароль должен быть не менее 6 символов'}), 400

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Пользователь {user.full_name} обновлен'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/user/<int:user_id>/delete', methods=['POST'])
@login_required
def api_delete_user(user_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403

    try:
        from modules.core.models import User, Order

        user = User.query.get_or_404(user_id)

        if user.id == current_user.id:
            return jsonify({'success': False, 'error': 'Нельзя удалить свою учетную запись'}), 400

        order_count = Order.query.filter_by(user_id=user_id).count()

        if order_count > 0:
            user.is_active = False
            db.session.commit()
            return jsonify({
                'success': True,
                'message': f'Пользователь {user.full_name} деактивирован (имеет {order_count} заказов)',
                'action': 'deactivated'
            })
        else:
            user_name = user.full_name
            db.session.delete(user)
            db.session.commit()
            return jsonify({
                'success': True,
                'message': f'Пользователь {user_name} удален',
                'action': 'deleted'
            })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/supply-request/<int:request_id>/details')
@login_required
def get_supply_request_details(request_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403

    from modules.core.models import SupplyRequest

    supply_request = SupplyRequest.query.get_or_404(request_id)

    urgency_text = {
        'high': 'Высокая',
        'medium': 'Средняя',
        'low': 'Низкая'
    }.get(supply_request.urgency, 'Не указана')

    return jsonify({
        'success': True,
        'request': {
            'id': supply_request.id,
            'product_name': supply_request.product_name,
            'quantity': supply_request.quantity,
            'unit': supply_request.unit,
            'urgency': supply_request.urgency,
            'urgency_text': urgency_text,
            'notes': supply_request.notes,
            'status': supply_request.status,
            'cook_name': supply_request.cook.full_name if supply_request.cook else 'Неизвестно',
            'created_at': supply_request.created_at.strftime('%d.%m.%Y %H:%M') if supply_request.created_at else '',
            'approved_by': supply_request.approved_by,
            'approver_name': supply_request.approver.full_name if supply_request.approver else '',
            'approved_at': supply_request.approved_at.strftime('%d.%m.%Y %H:%M') if supply_request.approved_at else ''
        }
    })


@admin_bp.route('/api/supply-request/<int:request_id>/process', methods=['POST'])
@login_required
def api_process_supply_request(request_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403

    try:
        from modules.core.models import SupplyRequest

        supply_request = SupplyRequest.query.get_or_404(request_id)
        data = request.json

        if 'status' not in data:
            return jsonify({'success': False, 'error': 'Не указан статус'}), 400

        old_status = supply_request.status
        supply_request.status = data['status']
        supply_request.approved_by = current_user.id
        supply_request.approved_at = datetime.utcnow()

        if 'notes' in data and data['notes']:
            supply_request.notes = (supply_request.notes or '') + f"\n[Админ {current_user.full_name}]: {data['notes']}"

        db.session.commit()

        status_text = "утверждена" if data['status'] == 'approved' else "отклонена"

        return jsonify({
            'success': True,
            'message': f'Заявка #{supply_request.id} {status_text}',
            'new_status': data['status']
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/supply-request/<int:request_id>/delete', methods=['POST'])
@login_required
def api_delete_supply_request(request_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403

    try:
        from modules.core.models import SupplyRequest

        supply_request = SupplyRequest.query.get_or_404(request_id)

        if supply_request.status == 'approved':
            return jsonify({'success': False, 'error': 'Нельзя удалить утвержденную заявку'}), 400

        db.session.delete(supply_request)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Заявка #{supply_request.id} удалена'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/report/generate', methods=['POST'])
@login_required
def api_generate_report():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403

    try:
        from modules.core.models import Order, User, MenuItem, SupplyRequest

        data = request.json
        report_type = data.get('report_type', 'daily')

        if report_type == 'daily':
            start_date = datetime.today().date()
            end_date = start_date
        elif report_type == 'weekly':
            end_date = datetime.today().date()
            start_date = end_date - timedelta(days=7)
        elif report_type == 'monthly':
            end_date = datetime.today().date()
            start_date = end_date - timedelta(days=30)
        elif report_type == 'custom':
            start_date = datetime.strptime(data.get('start_date'), '%Y-%m-%d').date()
            end_date = datetime.strptime(data.get('end_date'), '%Y-%m-%d').date()
        else:
            return jsonify({'success': False, 'error': 'Неверный тип отчета'}), 400

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
            'rejected': len([r for r in supply_requests if r.status == 'rejected']),
            'total_cost': 0  # Заглушка, так как нет поля estimated_cost
        }

        popular_dishes = db.session.query(
            Order.menu_item_id,
            db.func.count(Order.id).label('orders_count'),
            db.func.sum(Order.quantity).label('total_quantity')
        ).filter(
            Order.order_date >= start_date,
            Order.payment_status == 'paid'
        ).group_by(
            Order.menu_item_id
        ).order_by(
            db.func.count(Order.id).desc()
        ).limit(10).all()

        popular_dishes_data = []
        for dish in popular_dishes:
            menu_item = MenuItem.query.get(dish.menu_item_id)
            if menu_item:
                popular_dishes_data.append({
                    'name': menu_item.name,
                    'orders_count': dish.orders_count,
                    'total_quantity': dish.total_quantity,
                    'revenue': menu_item.price * dish.total_quantity
                })

        report = {
            'title': f'Отчет за период с {start_date.strftime("%d.%m.%Y")} по {end_date.strftime("%d.%m.%Y")}',
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
            'popular_dishes': popular_dishes_data,
            'generated_at': datetime.now().strftime('%d.%m.%Y %H:%M'),
            'generated_by': current_user.full_name
        }

        return jsonify({
            'success': True,
            'report': report,
            'download_url': f'/admin/api/report/download/{int(datetime.now().timestamp())}'
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/report/export')
@login_required
def export_report():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403

    try:
        from modules.core.models import Order, User, MenuItem, SupplyRequest

        report_type = request.args.get('report_type', 'daily')
        format_type = request.args.get('format', 'html')
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        if report_type == 'daily':
            start_date = datetime.today().date()
            end_date = start_date
        elif report_type == 'weekly':
            end_date = datetime.today().date()
            start_date = end_date - timedelta(days=7)
        elif report_type == 'monthly':
            end_date = datetime.today().date()
            start_date = end_date - timedelta(days=30)
        elif report_type == 'custom' and start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            return jsonify({'success': False, 'error': 'Неверные параметры отчета'}), 400

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
            'rejected': len([r for r in supply_requests if r.status == 'rejected']),
            'cancelled': len([r for r in supply_requests if r.status == 'cancelled'])
        }

        popular_dishes = db.session.query(
            Order.menu_item_id,
            db.func.count(Order.id).label('orders_count'),
            db.func.sum(Order.quantity).label('total_quantity')
        ).filter(
            Order.order_date >= start_date,
            Order.payment_status == 'paid'
        ).group_by(
            Order.menu_item_id
        ).order_by(
            db.func.count(Order.id).desc()
        ).limit(10).all()

        popular_dishes_data = []
        for dish in popular_dishes:
            menu_item = MenuItem.query.get(dish.menu_item_id)
            if menu_item:
                popular_dishes_data.append({
                    'name': menu_item.name,
                    'orders_count': dish.orders_count,
                    'total_quantity': dish.total_quantity,
                    'revenue': menu_item.price * dish.total_quantity
                })

        report = {
            'title': f'Отчет за период с {start_date.strftime("%d.%m.%Y")} по {end_date.strftime("%d.%m.%Y")}',
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
            'popular_dishes': popular_dishes_data,
            'generated_at': datetime.now().strftime('%d.%m.%Y %H:%M'),
            'generated_by': current_user.full_name
        }

        if format_type == 'txt':
            return export_to_txt(report)
        elif format_type == 'csv':
            return export_to_csv(report)
        elif format_type == 'html':
            return export_to_html(report)
        elif format_type == 'pdf':
            return export_to_pdf(report)
        else:
            return jsonify({'success': False, 'error': 'Неподдерживаемый формат'}), 400

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def export_to_txt(report):
    txt_content = f"""
ОТЧЕТ О РАБОТЕ ШКОЛЬНОЙ СТОЛОВОЙ
===================================

{report['title']}
Период: {report['period']['start_date']} - {report['period']['end_date']} ({report['period']['days']} дней)
Сгенерирован: {report['generated_at']}
Пользователь: {report['generated_by']}

1. СТАТИСТИКА ЗАКАЗОВ
---------------------
Всего заказов: {report['orders']['total']}
Оплаченных заказов: {report['orders']['paid']}
Получено заказов: {report['orders']['received']}
Общая выручка: {report['orders']['revenue']:.2f} ₽

2. СТАТИСТИКА ПОЛЬЗОВАТЕЛЕЙ
--------------------------
Всего пользователей: {report['users']['total']}
Активных пользователей (с заказами): {report['users']['active']}

3. ЗАЯВКИ НА ЗАКУПКУ
-------------------
Всего заявок: {report['supply_requests']['total']}
Утверждено: {report['supply_requests']['approved']}
Ожидают решения: {report['supply_requests']['pending']}
Отклонено: {report['supply_requests']['rejected']}
Отменено: {report['supply_requests']['cancelled']}

4. ПОПУЛЯРНЫЕ БЛЮДА
-------------------
"""

    for i, dish in enumerate(report['popular_dishes'], 1):
        txt_content += f"{i}. {dish['name']}\n"
        txt_content += f"   Заказов: {dish['orders_count']}\n"
        txt_content += f"   Порций: {dish['total_quantity']}\n"
        txt_content += f"   Выручка: {dish['revenue']:.2f} ₽\n\n"

    txt_content += "\n===================================\n"
    txt_content += "Конец отчета"

    response = make_response(txt_content)
    response.headers['Content-Type'] = 'text/plain; charset=utf-8'
    response.headers[
        'Content-Disposition'] = f'attachment; filename=report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'

    return response


def export_to_csv(report):
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)

    writer.writerow(['ОТЧЕТ О РАБОТЕ ШКОЛЬНОЙ СТОЛОВОЙ'])
    writer.writerow([report['title']])
    writer.writerow(['Период', f"{report['period']['start_date']} - {report['period']['end_date']}"])
    writer.writerow(['Сгенерирован', report['generated_at']])
    writer.writerow(['Пользователь', report['generated_by']])
    writer.writerow([])

    writer.writerow(['СТАТИСТИКА ЗАКАЗОВ'])
    writer.writerow(['Всего заказов', report['orders']['total']])
    writer.writerow(['Оплаченных заказов', report['orders']['paid']])
    writer.writerow(['Получено заказов', report['orders']['received']])
    writer.writerow(['Общая выручка', f"{report['orders']['revenue']:.2f} ₽"])
    writer.writerow([])

    writer.writerow(['СТАТИСТИКА ПОЛЬЗОВАТЕЛЕЙ'])
    writer.writerow(['Всего пользователей', report['users']['total']])
    writer.writerow(['Активных пользователей', report['users']['active']])
    writer.writerow([])

    writer.writerow(['ЗАЯВКИ НА ЗАКУПКУ'])
    writer.writerow(['Всего заявок', report['supply_requests']['total']])
    writer.writerow(['Утверждено', report['supply_requests']['approved']])
    writer.writerow(['Ожидают решения', report['supply_requests']['pending']])
    writer.writerow(['Отклонено', report['supply_requests']['rejected']])
    writer.writerow(['Отменено', report['supply_requests']['cancelled']])
    writer.writerow([])

    writer.writerow(['ПОПУЛЯРНЫЕ БЛЮДА'])
    writer.writerow(['№', 'Блюдо', 'Заказов', 'Порций', 'Выручка'])

    for i, dish in enumerate(report['popular_dishes'], 1):
        writer.writerow([
            i,
            dish['name'],
            dish['orders_count'],
            dish['total_quantity'],
            f"{dish['revenue']:.2f} ₽"
        ])

    csv_content = output.getvalue()
    output.close()

    response = make_response(csv_content)
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    response.headers[
        'Content-Disposition'] = f'attachment; filename=report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'

    return response


def export_to_html(report):
    html_content = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report['title']}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid #3498db;
            padding-bottom: 20px;
        }}
        .header h1 {{
            color: #2c3e50;
            margin-bottom: 10px;
        }}
        .section {{
            margin-bottom: 30px;
            page-break-inside: avoid;
        }}
        .section h2 {{
            color: #3498db;
            border-bottom: 1px solid #eee;
            padding-bottom: 10px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        .stat-card {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .stat-card h3 {{
            color: #2c3e50;
            margin-top: 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #f8f9fa;
            font-weight: 600;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .footer {{
            margin-top: 50px;
            text-align: center;
            color: #7f8c8d;
            font-size: 0.9rem;
            border-top: 1px solid #eee;
            padding-top: 20px;
        }}
        @media print {{
            body {{
                font-size: 12pt;
            }}
            .no-print {{
                display: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{report['title']}</h1>
        <p><strong>Период:</strong> {report['period']['start_date']} - {report['period']['end_date']} ({report['period']['days']} дней)</p>
        <p><strong>Сгенерирован:</strong> {report['generated_at']}</p>
        <p><strong>Пользователь:</strong> {report['generated_by']}</p>
    </div>

    <div class="section">
        <h2>1. Статистика заказов</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <h3>Всего заказов</h3>
                <p style="font-size: 2rem; font-weight: bold; color: #2c3e50;">{report['orders']['total']}</p>
            </div>
            <div class="stat-card">
                <h3>Оплаченных заказов</h3>
                <p style="font-size: 2rem; font-weight: bold; color: #27ae60;">{report['orders']['paid']}</p>
            </div>
            <div class="stat-card">
                <h3>Получено заказов</h3>
                <p style="font-size: 2rem; font-weight: bold; color: #3498db;">{report['orders']['received']}</p>
            </div>
            <div class="stat-card">
                <h3>Общая выручка</h3>
                <p style="font-size: 2rem; font-weight: bold; color: #e74c3c;">{report['orders']['revenue']:.2f} ₽</p>
            </div>
        </div>
    </div>

    <div class="section">
        <h2>2. Статистика пользователей</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <h3>Всего пользователей</h3>
                <p style="font-size: 2rem; font-weight: bold; color: #2c3e50;">{report['users']['total']}</p>
            </div>
            <div class="stat-card">
                <h3>Активных пользователей</h3>
                <p style="font-size: 2rem; font-weight: bold; color: #9b59b6;">{report['users']['active']}</p>
            </div>
        </div>
    </div>

    <div class="section">
        <h2>3. Заявки на закупку</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <h3>Всего заявок</h3>
                <p style="font-size: 2rem; font-weight: bold; color: #2c3e50;">{report['supply_requests']['total']}</p>
            </div>
            <div class="stat-card">
                <h3>Утверждено</h3>
                <p style="font-size: 2rem; font-weight: bold; color: #27ae60;">{report['supply_requests']['approved']}</p>
            </div>
            <div class="stat-card">
                <h3>Ожидают решения</h3>
                <p style="font-size: 2rem; font-weight: bold; color: #f39c12;">{report['supply_requests']['pending']}</p>
            </div>
            <div class="stat-card">
                <h3>Отклонено</h3>
                <p style="font-size: 2rem; font-weight: bold; color: #e74c3c;">{report['supply_requests']['rejected']}</p>
            </div>
        </div>
    </div>
"""

    if report['popular_dishes']:
        html_content += """
    <div class="section">
        <h2>4. Популярные блюда</h2>
        <table>
            <thead>
                <tr>
                    <th>№</th>
                    <th>Блюдо</th>
                    <th>Количество заказов</th>
                    <th>Всего порций</th>
                    <th>Выручка</th>
                </tr>
            </thead>
            <tbody>
"""

        for i, dish in enumerate(report['popular_dishes'], 1):
            html_content += f"""
                <tr>
                    <td>{i}</td>
                    <td><strong>{dish['name']}</strong></td>
                    <td>{dish['orders_count']}</td>
                    <td>{dish['total_quantity']}</td>
                    <td>{dish['revenue']:.2f} ₽</td>
                </tr>
"""

        html_content += """
            </tbody>
        </table>
    </div>
"""

    html_content += f"""
    <div class="footer">
        <p>Отчет сгенерирован автоматически системой управления школьной столовой</p>
        <p>Дата формирования: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}</p>
        <button class="no-print" onclick="window.print()" style="background: #3498db; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin-top: 10px;">
            📄 Распечатать отчет
        </button>
    </div>
</body>
</html>
"""

    response = make_response(html_content)
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    response.headers[
        'Content-Disposition'] = f'attachment; filename=report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html'

    return response


def export_to_pdf(report):
    pdf_content = f"""
Это PDF экспорт отчета
{report['title']}

Для использования PDF экспорта необходимо установить дополнительные библиотеки:
1. pip install reportlab (для создания PDF)
2. pip install weasyprint (для конвертации HTML в PDF)

Пока что используйте экспорт в HTML и печать в PDF через браузер.
"""

    response = make_response(pdf_content)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers[
        'Content-Disposition'] = f'attachment; filename=report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'

    return response


@admin_bp.route('/api/report/download/<int:timestamp>')
@login_required
def download_report(timestamp):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403

    from flask import make_response
    import json


    response = make_response(json.dumps({'message': 'Report file would be here'}, ensure_ascii=False))
    response.headers['Content-Type'] = 'application/json'
    response.headers['Content-Disposition'] = f'attachment; filename=report_{timestamp}.json'

    return response


@admin_bp.route('/api/feedback/<int:feedback_id>/delete', methods=['POST'])
@login_required
def delete_feedback(feedback_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403

    try:
        from modules.core.models import Feedback

        feedback = Feedback.query.get_or_404(feedback_id)
        db.session.delete(feedback)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Отзыв удален'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/feedback/<int:feedback_id>/reply', methods=['POST'])
@login_required
def reply_to_feedback(feedback_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403

    try:
        from modules.core.models import Feedback

        feedback = Feedback.query.get_or_404(feedback_id)
        data = request.json

        if 'reply' not in data or not data['reply']:
            return jsonify({'success': False, 'error': 'Введите текст ответа'}), 400

        feedback.admin_reply = data['reply']
        feedback.replied_at = datetime.utcnow()
        feedback.replied_by = current_user.id

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Ответ сохранен'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
