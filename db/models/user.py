
from uuid import UUID, uuid4
from .base import Base
from sqlalchemy.orm import Mapped, mapped_column


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tg_id: Mapped[int] = mapped_column(unique=True, index=True, nullable=False)
    rank: Mapped[float]
    admin: Mapped[bool]
    creator: Mapped[bool]
    

