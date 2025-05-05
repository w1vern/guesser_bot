

import asyncio
import mimetypes
import os

from minio import Minio

from config import settings
from db.main import DatabaseSessionManager, get_db_url
from db.repositories import FileRepository, QuestionRepository, UserRepository

directory_path = './content/'


async def main():
    DB_URL = get_db_url(user=settings.db_user, password=settings.db_password,
                               ip=settings.db_ip, port=settings.db_port, name=settings.db_name)
    session_manager = DatabaseSessionManager(DB_URL, {"echo": False})
    minio_client = Minio(
        endpoint=f"{settings.minio_ip}:{settings.minio_port}",
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure
    )
    async with session_manager.context_session() as session:
        ur = UserRepository(session)
        fr = FileRepository(session)
        qr = QuestionRepository(session)
        user = await ur.get_by_tg_id(settings.tg_admin_id)
        if user is None:
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
                minio_client.fput_object(settings.minio_bucket, str(
                    db_file.id), full_path, mime_type)
                q = await qr.create(file=db_file, creator=user, answers_count=4, rank=0.5)

if __name__ == "__main__":
    asyncio.run(main())
