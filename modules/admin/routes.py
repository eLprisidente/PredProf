from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from modules.core.database import db
from datetime import datetime, timedelta
from sqlalchemy import func, or_
import json

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
    """API для получения данных пользователя"""
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
    """API для добавления нового пользователя"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403

    try:
        from modules.core.models import User
        from modules.auth.utils import hash_password

        data = request.json

        # Валидация данных
        required_fields = ['full_name', 'email', 'password', 'role']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'success': False, 'error': f'Отсутствует поле: {field}'}), 400

        # Проверяем email
        if not '@' in data['email']:
            return jsonify({'success': False, 'error': 'Некорректный email'}), 400

        # Проверяем, существует ли пользователь с таким email
        existing_user = User.query.filter_by(email=data['email']).first()
        if existing_user:
            return jsonify({'success': False, 'error': 'Пользователь с таким email уже существует'}), 400

        # Проверяем пароль
        if len(data['password']) < 6:
            return jsonify({'success': False, 'error': 'Пароль должен быть не менее 6 символов'}), 400

        # Создаем нового пользователя
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
    """API для обновления пользователя"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403

    try:
        from modules.core.models import User
        from modules.auth.utils import hash_password

        user = User.query.get_or_404(user_id)
        data = request.json

        # Обновляем поля
        if 'full_name' in data:
            user.full_name = data['full_name']
        if 'email' in data and data['email'] != user.email:
            # Проверяем, не занят ли email
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

        # Если нужно обновить пароль
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
    """API для удаления пользователя"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403

    try:
        from modules.core.models import User, Order

        user = User.query.get_or_404(user_id)

        # Нельзя удалить самого себя
        if user.id == current_user.id:
            return jsonify({'success': False, 'error': 'Нельзя удалить свою учетную запись'}), 400

        # Проверяем, есть ли связанные заказы
        order_count = Order.query.filter_by(user_id=user_id).count()

        if order_count > 0:
            # Если есть заказы, делаем пользователя неактивным
            user.is_active = False
            db.session.commit()
            return jsonify({
                'success': True,
                'message': f'Пользователь {user.full_name} деактивирован (имеет {order_count} заказов)',
                'action': 'deactivated'
            })
        else:
            # Если заказов нет, удаляем полностью
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
    """API для получения деталей заявки"""
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
            'category': supply_request.category,
            'quantity': supply_request.quantity,
            'unit': supply_request.unit,
            'supplier': supply_request.supplier,
            'urgency': supply_request.urgency,
            'urgency_text': urgency_text,
            'reason': supply_request.reason,
            'notes': supply_request.notes,
            'status': supply_request.status,
            'cook_name': supply_request.cook.full_name if supply_request.cook else 'Неизвестно',
            'created_at': supply_request.created_at.strftime('%d.%m.%Y %H:%M') if supply_request.created_at else '',
            'approved_by': supply_request.approved_by,
            'approval_date': supply_request.approval_date.strftime(
                '%d.%m.%Y %H:%M') if supply_request.approval_date else ''
        }
    })


@admin_bp.route('/api/supply-request/<int:request_id>/process', methods=['POST'])
@login_required
def api_process_supply_request(request_id):
    """API для обработки заявки на закупку"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403

    try:
        from modules.core.models import SupplyRequest, Inventory

        supply_request = SupplyRequest.query.get_or_404(request_id)
        data = request.json

        if 'status' not in data:
            return jsonify({'success': False, 'error': 'Не указан статус'}), 400

        old_status = supply_request.status
        supply_request.status = data['status']
        supply_request.approved_by = current_user.id
        supply_request.approval_date = datetime.utcnow()

        if 'notes' in data and data['notes']:
            supply_request.notes = (supply_request.notes or '') + f"\n[Админ {current_user.full_name}]: {data['notes']}"

        # Если заявка утверждена, обновляем инвентарь
        if data['status'] == 'approved':
            # Ищем существующую запись в инвентаре
            inventory_item = Inventory.query.filter_by(
                product_name=supply_request.product_name
            ).first()

            if inventory_item:
                # Обновляем количество
                inventory_item.current_quantity += supply_request.quantity
                inventory_item.last_updated = datetime.utcnow()
            else:
                # Создаем новую запись
                inventory_item = Inventory(
                    product_name=supply_request.product_name,
                    current_quantity=supply_request.quantity,
                    unit=supply_request.unit,
                    min_quantity=supply_request.quantity * 0.5,  # 50% от заказанного
                    category=supply_request.category,
                    supplier=supply_request.supplier
                )
                db.session.add(inventory_item)

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
    """API для удаления заявки на закупку"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403

    try:
        from modules.core.models import SupplyRequest

        supply_request = SupplyRequest.query.get_or_404(request_id)

        # Можно удалять только отклоненные или устаревшие заявки
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
    """API для генерации отчета"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403

    try:
        from modules.core.models import Order, User, MenuItem, SupplyRequest

        data = request.json
        report_type = data.get('report_type', 'daily')

        # Определяем период
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

        # Собираем статистику по заказам
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

        # Статистика по пользователям
        users_with_orders = User.query.filter(
            User.orders.any(Order.order_date >= start_date)
        ).all()

        # Статистика по заявкам на закупку
        supply_requests = SupplyRequest.query.filter(
            SupplyRequest.created_at >= datetime.combine(start_date, datetime.min.time()),
            SupplyRequest.created_at <= datetime.combine(end_date, datetime.max.time())
        ).all()

        supply_stats = {
            'total': len(supply_requests),
            'approved': len([r for r in supply_requests if r.status == 'approved']),
            'pending': len([r for r in supply_requests if r.status == 'pending']),
            'rejected': len([r for r in supply_requests if r.status == 'rejected']),
            'total_cost': sum(r.estimated_cost or 0 for r in supply_requests if r.status == 'approved')
        }

        # Популярные блюда
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


@admin_bp.route('/api/report/download/<int:timestamp>')
@login_required
def download_report(timestamp):
    """API для скачивания отчета"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403

    from flask import make_response
    import json

    # Здесь можно реализовать генерацию PDF/Excel
    # Пока просто возвращаем JSON
    response = make_response(json.dumps({'message': 'Report file would be here'}, ensure_ascii=False))
    response.headers['Content-Type'] = 'application/json'
    response.headers['Content-Disposition'] = f'attachment; filename=report_{timestamp}.json'

    return response


@admin_bp.route('/api/feedback/<int:feedback_id>/delete', methods=['POST'])
@login_required
def delete_feedback(feedback_id):
    """API для удаления отзыва"""
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
    """API для ответа на отзыв"""
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