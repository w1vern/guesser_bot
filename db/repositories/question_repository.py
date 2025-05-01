

import re
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from db.models import User, File, Question


class QuestionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self,
                     file: File,
                     creator: User,
                     answers_count: int = 0,
                     rank: float = 0.5
                     ) -> Optional[Question]:
        question = Question(
            rank=rank,
            file_id=file.id,
            creator_id=creator.id,
            answer=file.answer,
            answers_count=answers_count)
        self.session.add(question)
        await self.session.flush()
        return await self.get_by_id(question.id)

    async def get_by_id(self, question_id: UUID) -> Optional[Question]:
        stmt = select(Question).where(Question.id == question_id)
        return await self.session.scalar(stmt)

    async def get_random_question(self) -> Question | None:
        stmt = select(Question).order_by(func.random()).limit(1)
        return await self.session.scalar(stmt)

    #TODO: trouble with ans multiplying because file type
    async def get_random_questions(self, count: int, exclude: list[Question] = []) -> list[Question]:
        exclude_answers = [q.answer for q in exclude]
        stmt = select(Question).where(Question.answer.not_in(
            exclude_answers)).order_by(func.random()).limit(count)
        return list((await self.session.scalars(stmt)).all())

    async def get_by_creator(self, creator: User) -> Optional[Question]:
        stmt = select(Question).where(Question.creator_id == creator.id)
        return await self.session.scalar(stmt)

    async def change_rank(self, question: Question, rank_diff: float) -> None:
        question.rank += rank_diff
        if question.rank <= 0 or question.rank >= 1:
            raise Exception("Rank must be between 0 and 1")
        await self.session.flush()
