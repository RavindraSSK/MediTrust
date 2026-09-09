.PHONY: install dev test lint format train frontend docker-up docker-down

PY ?= python3

install:
	$(PY) -m pip install -r backend/requirements-dev.txt -r ml/requirements.txt
	cd frontend && npm ci

dev:
	$(PY) -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8001 --reload

frontend:
	cd frontend && npm run dev

test:
	$(PY) -m pytest backend/tests ml/tests -p no:cacheprovider

lint:
	$(PY) -m ruff check backend ml
	$(PY) -m ruff format --check backend ml
	cd frontend && npm run lint

format:
	$(PY) -m ruff format backend ml
	$(PY) -m ruff check --fix backend ml

train:
	$(PY) ml/src/preprocess.py
	$(PY) ml/src/train_models.py

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down
