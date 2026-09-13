.PHONY: dev test eval-extract frontend-dev frontend-test frontend-build db-up db-down db-reset

dev:
	./scripts/dev.sh

test:
	pytest -v

eval-extract:
	python evals/run_extract_eval.py

db-up:
	docker compose up -d

db-down:
	docker compose down -v

db-reset: db-down db-up

frontend-dev:
	cd frontend && npm run dev

frontend-test:
	cd frontend && npm run test -- --run

frontend-build:
	cd frontend && npm run build
