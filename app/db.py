from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# SQLite URL
SQLALCHEMY_DATABASE_URL = "sqlite:///./app.db"

# Настройка движка
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Сессии
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовая модель
Base = declarative_base()
