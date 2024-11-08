# config.py
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from pydantic_settings import BaseSettings
from sqlalchemy import text
import asyncio


class Settings(BaseSettings):
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_NAME: str
    DB_PORT: int

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"



settings = Settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,
    pool_pre_ping=True,
    pool_recycle=3600
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)



class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
            print("Database connection successful")
            await conn.run_sync(Base.metadata.create_all)
            print("Database tables initialized")
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        raise


async def cleanup_db() -> None:
    try:
        await engine.dispose()
        await asyncio.sleep(1)
    except Exception as e:
        print(f"Error during cleanup: {str(e)}")
