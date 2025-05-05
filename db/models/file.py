from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class FileType(str, Enum):
    audio = "audio"
    video = "video"
    image = "image"


class File(Base):
    __tablename__ = "files"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    file_type: Mapped[str]
    answer: Mapped[str]
    description: Mapped[str]