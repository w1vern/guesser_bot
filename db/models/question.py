
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey

from .base import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .file import File
from .user import User

class QuestionType(str, Enum):
    select = "select"
    text = "text"

class Question(Base):
    __tablename__ = "questions"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    
    answers_count: Mapped[int]
    rank: Mapped[float]

    file_id: Mapped[UUID] = mapped_column(ForeignKey("files.id"))
    creator_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))

    file: Mapped[File] = relationship(lazy="selectin", foreign_keys=[file_id])
    creator: Mapped[User] = relationship(lazy="selectin", foreign_keys=[creator_id])