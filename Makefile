.PHONY: up down logs ps test lint fmt e2e race clean

up:        ## build and start everything (http://localhost:8080/docs)
	docker compose up -d --build

down:      ## stop (keeps data)
	docker compose down

clean:     ## stop and DELETE all data volumes
	docker compose down -v

logs:      ## follow logs of all services
	docker compose logs -f --tail=100

ps:
	docker compose ps

test:      ## unit + api tests (no Docker needed)
	python -m pytest -q

lint:
	ruff check .

fmt:
	ruff check . --fix

e2e:       ## full story against the running stack
	python -m labs.e2e_smoke

race:      ## atomic-counter experiment (restarts api with the rate limit lifted)
	docker compose -f docker-compose.yml -f docker-compose.lab.yml up -d --build api
	python -m labs.race_lab
	docker compose up -d api
