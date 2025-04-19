import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=f"{os.getenv('TARGET', 'dev')}.env")

    secret: str = "YOUR_SECRET"
    
    class Database:
        user: str = "postgres"
        password: str = "1234"
        ip: str = "postgres"
        port: int = 5432
        name: str = "deva_p1_db"
    
    class Redis:
        ip: str = "redis"
        port: int = 6379
    
    class Minio:
        ip: str = "minio"
        port: int = 9000
        access_key: str = "MINIO_ACCESS_KEY"
        secret_key: str = "NINIO_SECRET_KEY"
        bucket: str = "my-bucket"
        secure: bool = False
    

settings = Settings()