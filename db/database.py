from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator
import os

from db.models import Base


class Database:
    def __init__(self, db_url: str):
        """Инициализация подключения к базе данных."""
        self.engine = create_engine(db_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def create_tables(self):
        """Создание всех таблиц в базе данных."""
        Base.metadata.create_all(bind=self.engine)
        print("✓ Таблицы созданы успешно")
    
    def drop_tables(self):
        """Удаление всех таблиц из базы данных."""
        Base.metadata.drop_all(bind=self.engine)
        print("✓ Таблицы удалены")
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Контекстный менеджер для работы с сессией БД."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()


# Глобальный экземпляр базы данных
_db_instance = None


def init_database(db_url: str = None):
    """Инициализация глобального экземпляра базы данных."""
    global _db_instance
    if db_url is None:
        # По умолчанию используем PostgreSQL
        db_url = os.getenv(
            'DATABASE_URL',
            'postgresql://postgres:postgres@localhost:5432/neurocreatives'
        )
    # Заменяем postgresql:// на postgresql+psycopg:// для использования psycopg3
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgresql+psycopg://')
    _db_instance = Database(db_url)
    return _db_instance


def get_database() -> Database:
    """Получение глобального экземпляра базы данных."""
    global _db_instance
    if _db_instance is None:
        raise RuntimeError("База данных не инициализирована. Вызовите init_database() сначала.")
    return _db_instance


def get_db_session() -> Generator[Session, None, None]:
    """Dependency для FastAPI."""
    db = get_database()
    with db.get_session() as session:
        yield session
