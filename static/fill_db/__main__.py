

import asyncio
import os
import mimetypes

from minio import Minio

from db.repositories import FileRepository, QuestionRepository, UserRepository
from dependency_injector.wiring import inject, Provide
from sqlalchemy.ext.asyncio import AsyncSession
from di.di_implementation import Container as C
from config import settings



directory_path = '/content/'


@inject
async def main(session: AsyncSession = Provide[C.db_session], minio_client: Minio = Provide[C.minio_client]):
    container = C()
    container.wire(modules=[__name__])
    ur = UserRepository(session)
    fr = FileRepository(session)
    qr = QuestionRepository(session)
    user = await ur.create(tg_id=settings.tg_admin_id, admin=True, creator=True)
    if user is None:
        raise Exception("Admin user not created")
    for entry in os.listdir(directory_path):
        full_path = os.path.join(directory_path, entry)
        if os.path.isfile(full_path):
            mime_type = mimetypes.guess_type(full_path)[0]
            if mime_type is None:
                mime_type = 'unknown/unknown'
            basename = os.path.basename(full_path)
            name_no_ext, _ = os.path.splitext(basename)
            prefix = name_no_ext.split('_', 1)[0]
            db_file = await fr.create(file_type=mime_type, answer=prefix, description="")
            if db_file is None:
                raise Exception("File not created")
            minio_client.fput_object(settings.minio_bucket, str(db_file.id), full_path, mime_type)
            q = await qr.create(question_type='select', file=db_file, creator=user, rank=0.5)


if __name__ == "__main__":
    container = C()
    container.init_resources()         # если у вас есть Resource-провайдеры
    container.wire(modules=[__name__]) # чтобы понять, что инжектить

    # ВАЖНО: этот метод позаботится об инъекции Provide[…]
    asyncio.run(container.call_async(main))

    container.shutdown_resources()
