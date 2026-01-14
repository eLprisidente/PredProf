import os

# Структура файлов и их содержимое
templates = {
    'user/dashboard.html': '''{% extends "base.html" %}
{% block title %}Личный кабинет ученика{% endblock %}
{% block content %}
<h1>Личный кабинет ученика</h1>
<p>Добро пожаловать, {{ current_user.full_name }}</p>
<a href="{{ url_for('user.menu') }}" class="btn">Посмотреть меню</a>
{% endblock %}''',

    'user/menu.html': '''{% extends "base.html" %}
{% block title %}Меню{% endblock %}
{% block content %}
<h1>Меню</h1>
<p>Страница меню</p>
{% endblock %}''',

    'user/order.html': '''{% extends "base.html" %}
{% block title %}Заказ{% endblock %}
{% block content %}
<h1>Оформление заказа</h1>
<p>Форма заказа</p>
{% endblock %}''',

    'user/profile.html': '''{% extends "base.html" %}
{% block title %}Профиль{% endblock %}
{% block content %}
<h1>Профиль</h1>
<p>Настройки профиля</p>
{% endblock %}''',

    'cook/dashboard.html': '''{% extends "base.html" %}
{% block title %}Панель повара{% endblock %}
{% block content %}
<h1>Панель повара</h1>
<p>Добро пожаловать, {{ current_user.full_name }}</p>
{% endblock %}''',

    'admin/dashboard.html': '''{% extends "base.html" %}
{% block title %}Панель администратора{% endblock %}
{% block content %}
<h1>Панель администратора</h1>
<p>Добро пожаловать, {{ current_user.full_name }}</p>
{% endblock %}'''
}

# Создаем папки и файлы
for path, content in templates.items():
    dir_name = os.path.dirname(f'templates/{path}')
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)

    with open(f'templates/{path}', 'w', encoding='utf-8') as f:
        f.write(content)

print("Все шаблоны созданы!")