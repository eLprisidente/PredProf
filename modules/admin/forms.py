from flask_wtf import FlaskForm
from wtforms import SelectField, DateField, TextAreaField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Optional, Length
from datetime import datetime, timedelta


class ReportForm(FlaskForm):
    report_type = SelectField('Тип отчета', choices=[
        ('daily', 'Ежедневный'),
        ('weekly', 'Еженедельный'),
        ('monthly', 'Ежемесячный'),
        ('custom', 'Произвольный период')
    ], validators=[DataRequired()])

    start_date = DateField('Начало периода', default=datetime.today() - timedelta(days=30))
    end_date = DateField('Конец периода', default=datetime.today())

    include_payments = BooleanField('Включить данные об оплатах', default=True)
    include_orders = BooleanField('Включить данные о заказах', default=True)
    include_feedback = BooleanField('Включить отзывы', default=True)
    include_inventory = BooleanField('Включить инвентарь', default=False)

    submit = SubmitField('Сгенерировать отчет')


class ApprovalForm(FlaskForm):
    status = SelectField('Решение', choices=[
        ('approved', 'Утвердить'),
        ('rejected', 'Отклонить')
    ], validators=[DataRequired()])

    notes = TextAreaField('Комментарий к решению', validators=[
        Optional(),
        Length(max=500)
    ], render_kw={"placeholder": "Обоснование решения..."})

    submit = SubmitField('Принять решение')


class UserManagementForm(FlaskForm):
    action = SelectField('Действие', choices=[
        ('activate', 'Активировать'),
        ('deactivate', 'Деактивировать'),
        ('change_role', 'Изменить роль')
    ], validators=[DataRequired()])

    new_role = SelectField('Новая роль', choices=[
        ('student', 'Ученик'),
        ('cook', 'Повар'),
        ('admin', 'Администратор')
    ], validators=[Optional()])

    reason = TextAreaField('Причина', validators=[Optional(), Length(max=300)])

    submit = SubmitField('Выполнить')