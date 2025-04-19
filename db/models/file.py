from uuid import UUID, uuid4
from .base import Base
from sqlalchemy.orm import Mapped, mapped_column


class File(Base):
    __tablename__ = "files"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    file_type: 