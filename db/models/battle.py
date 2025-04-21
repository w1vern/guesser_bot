
from uuid import UUID, uuid4
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .user import User
from .question import Question

class Battle(Base):
    __tablename__ = "battles"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    question_id: Mapped[UUID] = mapped_column(ForeignKey("questions.id"))
    user_rank: Mapped[float]
    question_rank: Mapped[float]
    result: Mapped[bool]
    user_change: Mapped[float]
    question_change: Mapped[float]

    user: Mapped[User] = relationship(lazy="selectin", foreign_keys=[user_id])
    question: Mapped[Question] = relationship(lazy="selectin", foreign_keys=[question_id])