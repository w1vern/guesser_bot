
from unittest import result
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Protocol
from db.models import User, Question, Battle


class RankChangeFunction(Protocol):
    def __call__(self,
                 user_rank: float,
                 question_rank: float
                 ) -> tuple[float, float]:
        ...


class BattleRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self,
                     user: User,
                     question: Question,
                     result: bool,
                     rank_change_function: RankChangeFunction
                     ) -> Optional[Battle]:
        user_change, question_change = rank_change_function(user.rank, question.rank)
        battle = Battle(user_id=user.id,
                        question_id=question.id,
                        user_rank=user.rank,
                        question_rank=question.rank,
                        result=result,
                        user_change=user_change,
                        question_change=question_change)
        self.session.add(battle)
        await self.session.flush()
        return await self.get_by_id(battle.id)
    
    async def get_by_id(self, battle_id: UUID) -> Optional[Battle]:
        stmt = select(Battle).where(Battle.id == battle_id)
        return await self.session.scalar(stmt)
    
    async def get_by_user(self, user: User) -> list[Battle]:
        stmt = select(Battle).where(Battle.user_id == user.id)
        return list((await self.session.scalars(stmt)).all())
    
    async def get_by_question(self, question: Question) -> list[Battle]:
        stmt = select(Battle).where(Battle.question_id == question.id)
        return list((await self.session.scalars(stmt)).all())
