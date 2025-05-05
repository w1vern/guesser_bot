

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self,
                     tg_id: int,
                     rank: float = 0.5,
                     admin: bool = False,
                     creator: bool = False
                     ) -> Optional[User]:
        user = User(tg_id=tg_id, 
                    rank=rank, 
                    admin=admin, 
                    creator=creator)
        self.session.add(user)
        await self.session.flush()
        return await self.get_by_id(user.id)
    
    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        return await self.session.scalar(stmt)
    
    async def get_by_tg_id(self, tg_id: int) -> Optional[User]:
        stmt = select(User).where(User.tg_id == tg_id)
        return await self.session.scalar(stmt)
    
    async def change_rank(self, user: User, rank_diff: float) -> None:
        user.rank += rank_diff
        if user.rank <= 0 or user.rank >= 1:
            raise Exception("Rank must be between 0 and 1")
        await self.session.flush()

    async def set_creator(self, user: User) -> None:
        user.creator ^= True
        await self.session.flush()
