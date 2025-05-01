import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    model_config = SettingsConfigDict(env_file=f"{os.getenv('TARGET', 'dev')}.env")

    tg_bot_token: str = ""
    tg_admin_id: int = 0
        
    db_user: str = "postgres"
    db_password: str = "1234"
    db_ip: str = "postgres"
    db_port: int = 5432
    db_name: str = "guesser_bot_db"

    minio_ip: str = "minio"
    minio_port: int = 9000
    minio_access_key: str = "MINIO_ACCESS_KEY"
    minio_secret_key: str = "MINIO_SECRET_KEY"
    minio_bucket: str = "my-bucket"
    minio_secure: bool = False
    minio_user: str = "minioadmin"
    minio_password: str = "minioadmin"

    compose_profiles: str = ""

    

settings = Settings()
