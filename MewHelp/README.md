# MewHelp Ch01

FastAPI service scaffold for the MewHelp pure-chat chapter.

## Setup

From this directory, create and activate a virtual environment, then install the
dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in the required local settings in `.env`; do not commit that file.

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

OpenAPI is available at `http://127.0.0.1:8000/openapi.json`.

## Test

```bash
pytest tests/test_app.py -v
```
