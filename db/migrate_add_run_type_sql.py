"""
Миграция: добавление поля run_type в таблицу schedule_logs
Работает с PostgreSQL и SQLite через SQLAlchemy

Выполнение:
python db/migrate_add_run_type_sql.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text, inspect
import config

def migrate():
    """Добавить поле run_type в таблицу schedule_logs"""
    
    try:
        # Подключаемся к базе
        engine = create_engine(config.DATABASE_URL)
        
        with engine.connect() as conn:
            # Проверяем существует ли таблица
            inspector = inspect(engine)
            if 'schedule_logs' not in inspector.get_table_names():
                print("⚠️ Таблица schedule_logs не существует")
                print("✓ Таблица будет создана автоматически при следующем запуске приложения")
                return
            
            # Проверяем есть ли уже колонка run_type
            columns = [col['name'] for col in inspector.get_columns('schedule_logs')]
            
            if 'run_type' in columns:
                print("✓ Поле run_type уже существует в таблице schedule_logs")
                return
            
            # Добавляем колонку run_type
            print("Добавление поля run_type в таблицу schedule_logs...")
            
            # Для PostgreSQL и SQLite синтаксис похож
            conn.execute(text("""
                ALTER TABLE schedule_logs 
                ADD COLUMN run_type VARCHAR(20) DEFAULT 'auto' NOT NULL
            """))
            conn.commit()
            
            print("✓ Поле run_type успешно добавлено в таблицу schedule_logs")
            print("✓ Все существующие записи получили значение по умолчанию 'auto'")
            
    except Exception as e:
        print(f"❌ Ошибка при миграции: {e}")
        print("\nПопробуйте один из вариантов:")
        print("1. Перезапустите приложение - таблица пересоздастся с новой структурой")
        print("2. Удалите таблицу вручную: DROP TABLE schedule_logs;")

if __name__ == '__main__':
    migrate()
