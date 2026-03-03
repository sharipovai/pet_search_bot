from datetime import datetime, UTC
import enum
from sqlalchemy import String, Integer, DateTime, Enum, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from pgvector.sqlalchemy import Vector
import config

# 1. Настройки подключения (асинхронный драйвер postgresql+asyncpg)
DATABASE_URL = f"postgresql+asyncpg://{config.database_login}:{config.database_password}@localhost/{config.database_name}"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

# Статусы питомца
class PetStatus(str, enum.Enum):
    LOST = "lost"      # Потерян
    FOUND = "found"    # Найден

# 2. Описание таблицы
class Pet(Base):
    __tablename__ = "pets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(50)) # "dog" или "cat"
    status: Mapped[PetStatus] = mapped_column(Enum(PetStatus))
    city: Mapped[str] = mapped_column(String(100), index=True) # index нужен для быстрого поиска
    photo_id: Mapped[str] = mapped_column(String(255)) # ID файла из Telegram
    tg_id: Mapped[int] = mapped_column(Integer) # ID пользователя
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(UTC)
    )
    
    # Тот самый вектор! Указываем размерность модели (например, 384)
    embedding: Mapped[list[float]] = mapped_column(Vector(384))

# Функция для создания таблиц при старте бота
async def init_db():
    async with engine.begin() as conn:
        # ОБЯЗАТЕЛЬНО: создаем расширение pgvector в самой БД
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        # Создаем таблицы
        await conn.run_sync(Base.metadata.create_all)