""" 
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.main import DatabaseSessionManager, get_db_url
from db.redis import get_redis_client
from db.s3 import get_s3_client
from db.repositories.user_repository import UserRepository
from db.models.user import User
from aiogram.types import Message

from typing import Optional





class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        packages=["bot"]
    )

    config = providers.Configuration()

    db_url = providers.Singleton(
        get_db_url,
        user=settings.db_user,
        password=settings.db_password,
        ip=settings.db_ip,
        port=settings.db_port,
        name=settings.db_name,
    )

    db_manager = providers.Singleton(
        DatabaseSessionManager,
        host=db_url,
        engine_kwargs={"echo": True},
    )

    db_session = providers.Resource(
        lambda manager: manager.session(),
        manager=db_manager,
    )

    redis_client = providers.Singleton(get_redis_client)

    minio_client = providers.Singleton(get_s3_client)

    get_user = providers.Factory(
        get_user,
        session=db_session,
    )
 """