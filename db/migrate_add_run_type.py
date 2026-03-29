"""
Миграция: добавление поля run_type в таблицу schedule_logs

Выполнение:
python db/migrate_add_run_type.py
"""

import sqlite3
import os

DB_PATH = 'neurocreatives.db'

def migrate():
    """Добавить поле run_type в таблицу schedule_logs"""
    
    if not os.path.exists(DB_PATH):
        print(f"❌ База данных {DB_PATH} не найдена")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Проверяем, есть ли уже поле run_type
        cursor.execute("PRAGMA table_info(schedule_logs)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'run_type' in columns:
            print("✓ Поле run_type уже существует в таблице schedule_logs")
        else:
            # Добавляем поле run_type
            cursor.execute("""
                ALTER TABLE schedule_logs 
                ADD COLUMN run_type VARCHAR(20) DEFAULT 'auto' NOT NULL
            """)
            conn.commit()
            print("✓ Поле run_type успешно добавлено в таблицу schedule_logs")
        
    except sqlite3.Error as e:
        print(f"❌ Ошибка при миграции: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
