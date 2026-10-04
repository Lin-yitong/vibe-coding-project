.PHONY: dev test test-mysql-integration eval-extract eval-tools frontend-dev frontend-test frontend-build db-up db-down db-reset

MEWHELP_MYSQL_PORT ?= 3306
MEWHELP_MYSQL_INTEGRATION_URL ?= mysql+pymysql://mewhelp:mewhelp@127.0.0.1:$(MEWHELP_MYSQL_PORT)/mewhelp?charset=utf8mb4

dev:
	./scripts/dev.sh

test:
	pytest -v

test-mysql-integration:
	MEWHELP_RUN_MYSQL_INTEGRATION=1 MEWHELP_MYSQL_INTEGRATION_URL='$(MEWHELP_MYSQL_INTEGRATION_URL)' pytest tests/integration/test_mysql_schema.py -v

eval-extract:
	python evals/run_extract_eval.py

eval-tools:
	PYTHONPATH=. python evals/run_tool_eval.py

db-up:
	MEWHELP_MYSQL_PORT=$(MEWHELP_MYSQL_PORT) docker compose up -d --wait

db-down:
	docker compose down -v

db-reset: db-down db-up

frontend-dev:
	cd frontend && npm run dev

frontend-test:
	cd frontend && npm run test -- --run

frontend-build:
	cd frontend && npm run build
