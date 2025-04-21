
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from db.models import File

class FileRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, 
                     file_type: str, 
                     answer: str, 
                     description: str = ""
                     ) -> Optional[File]:
        file = File(file_type=file_type, 
                    answer=answer, 
                    description=description)
        self.session.add(file)
        await self.session.flush()
        return await self.get_by_id(file.id)
    
    async def get_by_id(self, file_id: UUID) -> Optional[File]:
        stmt = select(File).where(File.id == file_id)
        return await self.session.scalar(stmt)
    
    async def get_all(self) -> list[File]:
        stmt = select(File)
        return list((await self.session.scalars(stmt)).all())