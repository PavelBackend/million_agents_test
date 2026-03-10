DC = docker compose
EXEC = docker exec
LOGS = docker logs
ENV = --env-file .env
APP_FILE = ./deploy/docker-compose.yml
APP_CONTAINER = million_agents_service

.PHONY: app
app:
	${DC} -f ${APP_FILE} ${ENV} up --build -d

.PHONY: app-down
app-down:
	${DC} -f ${APP_FILE} down

.PHONY: app-shell
app-shell:
	${EXEC} ${APP_CONTAINER} bash

.PHONY: app-logs
app-logs:
	${LOGS} ${APP_CONTAINER} -f

.PHONY: test
test:
	${EXEC} ${APP_CONTAINER} python -m pytest -v

.PHONY: all
all: app
	@echo "Waiting for application startup..."
	@sleep 15
	$(MAKE) test
