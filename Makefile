

.PHONY: back

bot:
	set TARGET=dev&& python -m bot

back_install:
	uv install

redis:
	docker start Redis

postgres:
	docker start PostgreSQL


create_postgres:
	docker run --name PostgreSQL -p 5432:5432 -e POSTGRES_PASSWORD=1234 -d postgres

create_redis:
	docker run --name Redis -p 6379:6379 -d redis

create_minio:
	docker run -d \
	--name Minio \
	-p 9000:9000 \
	-p 9001:9001 \
	-e "MINIO_ROOT_USER=minioadmin" \
	-e "MINIO_ROOT_PASSWORD=minioadmin" \
	-v /mnt/data:/data \
	quay.io/minio/minio server /data --console-address ":9001"
	
minio:
	docker start Minio

gen_migration:
	set TARGET=dev&& alembic revision --autogenerate -m "first migration"

migration:
	alembic upgrade head

down_migration:
	alembic downgrade -1

delete_migrations:
	del db\migrations\versions\*

