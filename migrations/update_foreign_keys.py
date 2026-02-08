import sqlite3
import os
import sys
from pathlib import Path


def update_foreign_keys():
    """Обновляет внешние ключи для каскадного удаления пользователей"""
    db_path = 'instance/school_cafeteria.db'

    if not os.path.exists(db_path):
        print(f"База данных не найдена: {db_path}")
        return False

    backup_path = f"{db_path}.backup"

    try:
        # Создаем резервную копию
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"Создана резервная копия: {backup_path}")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Отключаем проверку внешних ключей
        cursor.execute("PRAGMA foreign_keys = OFF")

        # Временно отключаем внешние ключи
        cursor.execute("PRAGMA defer_foreign_keys = ON")

        # Список таблиц для обновления
        tables_to_update = [
            {
                'table': 'subscriptions',
                'foreign_key': 'user_id',
                'references': 'users(id)',
                'on_delete': 'CASCADE'
            },
            {
                'table': 'orders',
                'foreign_key': 'user_id',
                'references': 'users(id)',
                'on_delete': 'CASCADE'
            },
            {
                'table': 'feedbacks',
                'foreign_key': 'user_id',
                'references': 'users(id)',
                'on_delete': 'CASCADE'
            },
            {
                'table': 'transactions',
                'foreign_key': 'user_id',
                'references': 'users(id)',
                'on_delete': 'CASCADE'
            },
            {
                'table': 'supply_requests',
                'foreign_key': 'cook_id',
                'references': 'users(id)',
                'on_delete': 'SET NULL'
            },
            {
                'table': 'supply_requests',
                'foreign_key': 'approved_by',
                'references': 'users(id)',
                'on_delete': 'SET NULL'
            }
        ]

        # Для каждой таблицы создаем новую с правильными ключами
        for table_info in tables_to_update:
            table_name = table_info['table']
            fk_column = table_info['foreign_key']

            print(f"\nОбновляем таблицу: {table_name}")

            # Получаем информацию о таблице
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()

            if not columns:
                print(f"  Таблица {table_name} не существует, пропускаем")
                continue

            # Создаем список колонок для нового CREATE TABLE
            column_defs = []
            for col in columns:
                col_id, col_name, col_type, not_null, default_val, pk = col

                # Определяем тип данных
                if col_type is None:
                    col_type = "TEXT"

                # Формируем определение колонки
                col_def = f"{col_name} {col_type}"
                if not_null:
                    col_def += " NOT NULL"
                if default_val is not None:
                    col_def += f" DEFAULT {default_val}"
                if pk:
                    col_def += " PRIMARY KEY"

                column_defs.append(col_def)

            # Создаем временную таблицу
            temp_table_name = f"{table_name}_temp"

            # Удаляем временную таблицу, если существует
            cursor.execute(f"DROP TABLE IF EXISTS {temp_table_name}")

            # Создаем новую таблицу с правильными внешними ключами
            create_sql = f"""
            CREATE TABLE {temp_table_name} (
                {', '.join(column_defs)}
            """

            # Добавляем внешние ключи если они есть в списке
            if table_info.get('foreign_key'):
                create_sql += f""",
                FOREIGN KEY ({fk_column}) REFERENCES {table_info['references']}
                ON DELETE {table_info['on_delete']}
                """

            create_sql += ")"

            cursor.execute(create_sql)

            # Копируем данные из старой таблицы
            cursor.execute(f"INSERT INTO {temp_table_name} SELECT * FROM {table_name}")

            # Удаляем старую таблицу
            cursor.execute(f"DROP TABLE {table_name}")

            # Переименовываем временную таблицу
            cursor.execute(f"ALTER TABLE {temp_table_name} RENAME TO {table_name}")

            print(f"  Таблица {table_name} успешно обновлена")

        # Включаем проверку внешних ключей
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute("PRAGMA defer_foreign_keys = OFF")

        conn.commit()

        print("\n" + "=" * 50)
        print("Миграция завершена успешно!")
        print("=" * 50)

        # Проверяем структуру
        print("\nПроверка структуры таблиц:")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()

        for table_name, in tables:
            print(f"\nТаблица: {table_name}")
            cursor.execute(f"PRAGMA foreign_key_list({table_name})")
            fks = cursor.fetchall()
            for fk in fks:
                print(f"  FK: {fk[3]} -> {fk[2]}.{fk[4]} (ON DELETE: {fk[6]})")

        conn.close()
        return True

    except Exception as e:
        print(f"\nОшибка миграции: {e}")

        # Восстанавливаем из резервной копии
        if os.path.exists(backup_path):
            print("Восстанавливаем из резервной копии...")
            shutil.copy2(backup_path, db_path)

        return False


if __name__ == "__main__":
    update_foreign_keys()
