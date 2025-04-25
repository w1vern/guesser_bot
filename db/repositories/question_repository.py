

from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from db.models import User, File, Question

class QuestionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self,
                     question_type: str,
                     file: File,
                     creator: User,
                     rank: float = 0.5
                     ) -> Optional[Question]:
        question = Question(question_type=question_type,
                            rank=rank,
                            file_id=file.id,
                            creator_id=creator.id)
        self.session.add(question)
        await self.session.flush()
        return await self.get_by_id(question.id)
    
    async def get_by_id(self, question_id: UUID) -> Optional[Question]:
        stmt = select(Question).where(Question.id == question_id)
        return await self.session.scalar(stmt)
    
    async def get_by_creator(self, creator: User) -> Optional[Question]:
        stmt = select(Question).where(Question.creator_id == creator.id)
        return await self.session.scalar(stmt)
    
    async def change_rank(self, question: Question, rank_diff: float) -> None:
        question.rank += rank_diff
        if question.rank <= 0 or question.rank >= 1:
            raise Exception("Rank must be between 0 and 1")
        await self.session.flush()