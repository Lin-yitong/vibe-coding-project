.PHONY: dev test eval-extract frontend-dev frontend-test frontend-build

dev:
	./scripts/dev.sh

test:
	pytest -v

eval-extract:
	python evals/run_extract_eval.py

frontend-dev:
	cd frontend && npm run dev

frontend-test:
	cd frontend && npm run test -- --run

frontend-build:
	cd frontend && npm run build
