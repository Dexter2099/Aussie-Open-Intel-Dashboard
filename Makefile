COMPOSE=docker compose --env-file .env

.PHONY: up down logs psql ps build initdb

up:
	$(COMPOSE) up --build

down:
	$(COMPOSE) down -v

logs:
	$(COMPOSE) logs -f

ps:
	$(COMPOSE) ps

psql:
	$(COMPOSE) exec db psql -U $$POSTGRES_USER -d $$POSTGRES_DB

build:
	$(COMPOSE) build

initdb:
	@echo "Database schema initializes automatically via init scripts."
