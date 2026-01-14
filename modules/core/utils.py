from werkzeug.security import generate_password_hash
from .database import db
from .models import User


def create_default_admin():
    """Создание администратора по умолчанию"""
    admin = User.query.filter_by(email='admin@school.ru').first()

    if not admin:
        hashed_password = generate_password_hash('admin123', method='pbkdf2:sha256')
        admin = User(
            email='admin@school.ru',
            password=hashed_password,
            role='admin',
            full_name='Администратор Системы',
            is_active=True
        )
        db.session.add(admin)
        db.session.commit()
        print('✅ Создан администратор по умолчанию: admin@school.ru / admin123')

    return admin


def create_test_users():
    """Создание тестовых пользователей"""
    # Повар
    cook = User.query.filter_by(email='cook@school.ru').first()
    if not cook:
        hashed_password = generate_password_hash('cook123', method='pbkdf2:sha256')
        cook = User(
            email='cook@school.ru',
            password=hashed_password,
            role='cook',
            full_name='Иванов Иван Иванович',
            is_active=True
        )
        db.session.add(cook)

    # Ученик
    student = User.query.filter_by(email='student@school.ru').first()
    if not student:
        hashed_password = generate_password_hash('student123', method='pbkdf2:sha256')
        student = User(
            email='student@school.ru',
            password=hashed_password,
            role='student',
            full_name='Петров Петр Петрович',
            class_group='10А',
            is_active=True
        )
        db.session.add(student)

    db.session.commit()
    print('✅ Созданы тестовые пользователи')
    print('   Повар: cook@school.ru / cook123')
    print('   Ученик: student@school.ru / student123')