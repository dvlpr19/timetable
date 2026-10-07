COMPOSE = docker compose
BACKEND = $(COMPOSE) run --rm --no-deps backend
BACKEND_DB = $(COMPOSE) run --rm backend
FRONTEND = $(COMPOSE) run --rm --no-deps frontend

.PHONY: up down build logs migrate seed test test-backend test-frontend lint format shell makemessages

up:
	@test -f .env || cp .env.example .env
	$(COMPOSE) up -d --build
	@echo "Frontend: http://localhost:$${FRONTEND_HOST_PORT:-5173}  API: http://localhost:$${BACKEND_HOST_PORT:-8010}/api/docs/"

down:
	$(COMPOSE) down

build:
	$(COMPOSE) build

logs:
	$(COMPOSE) logs -f --tail=100

migrate:
	$(BACKEND_DB) python manage.py migrate

seed:
	$(BACKEND_DB) python manage.py seed_demo

test: lint test-backend test-frontend

test-backend:
	$(BACKEND_DB) sh -c "python manage.py compilemessages -v 0 && pytest"

test-frontend:
	$(FRONTEND) sh -c "npm run typecheck && npm test"

lint:
	$(BACKEND) sh -c "ruff check . && ruff format --check ."
	$(FRONTEND) sh -c "npm run lint && npm run format:check"

format:
	$(BACKEND) sh -c "ruff check --fix . && ruff format ."
	$(FRONTEND) npm run format

makemessages:
	$(BACKEND) python manage.py makemessages -l uz -l ru -l en --ignore=tests

shell:
	$(BACKEND_DB) python manage.py shell
