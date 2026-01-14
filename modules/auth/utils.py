from werkzeug.security import generate_password_hash, check_password_hash


def hash_password(password):
    """Хеширование пароля"""
    return generate_password_hash(password)


def verify_password(password_hash, password):
    """Проверка пароля"""
    return check_password_hash(password_hash, password)