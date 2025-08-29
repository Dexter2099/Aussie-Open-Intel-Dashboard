COMPOSE=docker compose -f infra/docker-compose.yml --env-file .env

.PHONY: up down logs build ps initdb

up:
	$(COMPOSE) up --build

down:
	$(COMPOSE) down -v

logs:
	$(COMPOSE) logs -f

ps:
	$(COMPOSE) ps

build:
	$(COMPOSE) build

initdb:
	@echo "Database schema initializes automatically via init scripts."

