import contextlib
from typing import Any, AsyncGenerator, AsyncIterator

from sqlalchemy.ext.asyncio import (AsyncConnection, AsyncSession,
                                    async_sessionmaker, create_async_engine)

from db.models.base import Base


class DatabaseSessionManager:
    def __init__(self, host: str, engine_kwargs: dict[str, Any] = {}):
        self._engine = create_async_engine(host, **engine_kwargs)
        self._sessionmaker = async_sessionmaker(
            autocommit=False, bind=self._engine, expire_on_commit=False)

    async def close(self):
        if self._engine is None:
            raise Exception("DatabaseSessionManager is not initialized")
        await self._engine.dispose()

        self._engine = None
        self._sessionmaker = None

    @contextlib.asynccontextmanager
    async def connect(self) -> AsyncIterator[AsyncConnection]:
        if self._engine is None:
            raise Exception("DatabaseSessionManager is not initialized")

        async with self._engine.begin() as connection:
            try:
                yield connection
            except Exception:
                await connection.rollback()
                raise

    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        if self._sessionmaker is None:
            raise Exception("DatabaseSessionManager is not initialized")

        session = self._sessionmaker()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    @contextlib.asynccontextmanager
    async def context_session(self) -> AsyncIterator[AsyncSession]:
        async for session in self.session():
            yield session


    async def create_db_and_tables(self):
        async with self.connect() as conn:
            await conn.run_sync(Base.metadata.create_all)


def get_db_postgres_url(user: str, password: str, ip: str, port: int, name: str) -> str:
    return f"postgresql+asyncpg://{user}:{password}@{ip}:{port}/{name}"

def get_db_sqlite_url(user: str, password: str, ip: str, port: int, name: str) -> str:
    return f"sqlite+aiosqlite:///{name}.db"

get_db_url = get_db_postgres_url

# session_manager = DatabaseSessionManager(DATABASE_URL, {"echo": False})