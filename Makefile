.PHONY: up down clean logs

up:
	docker compose up --build

down:
	docker compose down

clean:
	docker compose down -v --rmi local

logs:
	docker compose logs -f
