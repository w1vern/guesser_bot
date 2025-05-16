

from typing import Annotated, Awaitable, Protocol

from aiogram import types
from aiogram.fsm.context import FSMContext
from fast_depends import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.main import DatabaseSessionManager, GetDBUrl, get_db_postgres_url
from db.models import User
from db.repositories import UserRepository

get_db_url: GetDBUrl = get_db_postgres_url

session_manager = DatabaseSessionManager(
    get_db_url(
        user=settings.db_user,
        password=settings.db_password,
        ip=settings.db_ip,
        port=settings.db_port,
        name=settings.db_name
    ), {"echo": False}
)

Session = Annotated[AsyncSession, Depends(session_manager.session)]


async def get_user(message: types.Message,
                   session: Session
                   ) -> User:
    if not message.from_user:
        raise Exception("something 16")
    ur = UserRepository(session)
    user = await ur.get_by_tg_id(message.from_user.id)
    if user:
        return user
    raise Exception("something 3")
GetUser = Annotated[User, Depends(get_user)]


async def register_user(message: types.Message,
                        session: Session
                        ) -> User:
    if not message.from_user:
        raise Exception("something 16")
    ur = UserRepository(session)
    user = await ur.get_by_tg_id(message.from_user.id)
    if user:
        return user
    user = await ur.create(message.from_user.id)
    if not user:
        raise Exception("something 7")
    return user
CreateUser = Annotated[User, Depends(register_user)]


class Handler(Protocol):
    def __call__(self,
                 message: types.Message,
                 state: FSMContext,
                 user: User,
                 session: AsyncSession
                 ) -> Awaitable[None]:
        ...
