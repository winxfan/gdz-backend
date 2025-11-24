PY=python3
PIP=pip3

.PHONY: dev up down migrate revision seed

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

up:
	docker compose -f backend/docker-compose.yml up -d --build

down:
	docker compose -f backend/docker-compose.yml down -v

migrate:
	alembic upgrade head

revision:
	alembic revision --autogenerate -m "auto"

seed:
	$(PY) backend/scripts/seed.py

